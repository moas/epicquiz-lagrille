<script lang="ts">
	import { onMount } from 'svelte';
	import { createQueryConfig, deleteQueryConfig, getEpisode, getEpisodeQuestions, getQueryConfigs, selectEpisodeQuestion, unselectEpisodeQuestion, type Episode, type PaginatedEpisodeQuestions, type QueryConfig } from '$lib/episodes-api';
	import type { PageProps } from './$types';

	let { params }: PageProps = $props();
	let episode = $state<Episode | null>(null);
	let configs = $state<QueryConfig[]>([]);
	let questionPage = $state<PaginatedEpisodeQuestions | null>(null);
	let tags = $state('');
	let selectedLevel = $state('all');
	let mode = $state<'select' | 'unselect'>('select');
	let join = $state<'and' | 'or'>('and');
	let search = $state('');
	let filterLevel = $state('all');
	let currentPage = $state(1);
	let isLoading = $state(true);
	let isSavingRule = $state(false);
	let removingRuleId = $state<string | null>(null);
	let pendingQuestionId = $state<string | null>(null);
	let errorMessage = $state('');
	let ruleError = $state('');
	let questionError = $state('');
	let isRulesCollapsed = $state(false);

	function ruleTags(config: QueryConfig) { return config.tags?.length ? config.tags.join(' · ') : 'Tous les tags'; }
	function ruleLevels(config: QueryConfig) { return config.level?.length ? config.level.map((level) => `Niveau ${level}`).join(' · ') : 'Tous les niveaux'; }

	function questionParameters(page = currentPage) {
		const parameters = new URLSearchParams({ page: String(page) });
		if (search.trim()) parameters.set('search', search.trim());
		if (filterLevel !== 'all') parameters.set('level', filterLevel);
		return parameters;
	}

	async function loadQuestions(page = currentPage) {
		questionError = '';
		questionPage = await getEpisodeQuestions(params.id, questionParameters(page));
		currentPage = page;
	}

	async function load() {
		try {
			[episode, configs] = await Promise.all([getEpisode(params.id), getQueryConfigs(params.id)]);
			await loadQuestions(1);
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Impossible de charger les questions.';
		} finally {
			isLoading = false;
		}
	}

	onMount(() => { void load(); });

	async function addConfig() {
		isSavingRule = true; ruleError = '';
		try {
			configs = [...configs, await createQueryConfig(params.id, { mode, join, tags: tags.split(',').map((tag) => tag.trim()).filter(Boolean), level: selectedLevel === 'all' ? [] : [Number(selectedLevel)] })];
			tags = ''; selectedLevel = 'all';
			await loadQuestions(1);
		} catch (error) { ruleError = error instanceof Error ? error.message : 'Impossible d’ajouter cette règle. Réessayez.'; } finally { isSavingRule = false; }
	}

	async function removeConfig(id: string) {
		removingRuleId = id; ruleError = '';
		try { await deleteQueryConfig(params.id, id); configs = configs.filter((config) => config.id !== id); await loadQuestions(1); } catch (error) { ruleError = error instanceof Error ? error.message : 'Impossible de supprimer cette règle. Réessayez.'; } finally { removingRuleId = null; }
	}

	async function toggleQuestion(questionId: string, isSelected: boolean) {
		pendingQuestionId = questionId; questionError = '';
		try { if (isSelected) await unselectEpisodeQuestion(params.id, questionId); else await selectEpisodeQuestion(params.id, questionId); await loadQuestions(); } catch (error) { questionError = error instanceof Error ? error.message : 'Impossible de mettre à jour la sélection.'; } finally { pendingQuestionId = null; }
	}
</script>

<main>
	<a href={`/episodes/${params.id}`}>← Retour à l’épisode</a>
	{#if isLoading}<p class="loading">Chargement…</p>
	{:else if episode}
		<header><p>Épisode · {episode.title}</p><h1>Questions</h1><span>Préparez le pool de questions de la session</span></header>

		<section class="rules" class:collapsed={isRulesCollapsed} aria-labelledby="rules-title">
			<div class="rules-heading"><div><p class="eyebrow">Étape 1 · Critères</p><h2 id="rules-title">Règles de sélection</h2><p>Les règles déterminent les questions pouvant être utilisées dans cet épisode.</p></div><div class="rules-controls"><span class="rule-count">{configs.length} règle{configs.length === 1 ? '' : 's'}</span><button class="rules-toggle" type="button" aria-expanded={!isRulesCollapsed} aria-controls="rules-content" onclick={() => isRulesCollapsed = !isRulesCollapsed}>{isRulesCollapsed ? 'Développer' : 'Réduire'}<svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4" /></svg></button></div></div>
			{#if !isRulesCollapsed}<div id="rules-content">
			<form class="rule-builder" onsubmit={(event) => { event.preventDefault(); void addConfig(); }}>
				<div class="builder-heading"><strong>Ajouter un critère</strong><span>Les critères vides couvrent toute la bibliothèque.</span></div>
				<div class="rule-fields"><label for="rule-mode"><span>Action</span><select id="rule-mode" bind:value={mode} disabled={isSavingRule}><option value="select">Inclure les questions</option><option value="unselect">Exclure les questions</option></select></label><label for="rule-join"><span>Relation</span><select id="rule-join" bind:value={join} disabled={isSavingRule}><option value="and">Tous les critères (ET)</option><option value="or">Au moins un critère (OU)</option></select></label><label for="rule-tags"><span>Tags</span><input id="rule-tags" bind:value={tags} placeholder="Histoire, sport, cinéma…" disabled={isSavingRule} /></label><label for="rule-level"><span>Niveau</span><select id="rule-level" bind:value={selectedLevel} disabled={isSavingRule}><option value="all">Tous les niveaux</option>{#each [1,2,3,4,5] as level}<option value={String(level)}>Niveau {level}</option>{/each}</select></label></div>
				<div class="builder-actions"><p>Ajoutez au moins une règle <strong>Inclure</strong> pour alimenter le pool.</p><button disabled={isSavingRule}>{isSavingRule ? 'Ajout…' : 'Ajouter la règle'}</button></div>
			</form>
			<div class="active-rules"><div class="active-rules-heading"><h3>Règles actives</h3><span>Appliquées dans cet ordre</span></div>{#each configs as config, index}<article class:exclude={config.mode === 'unselect'} class="rule-card"><div class="rule-index">{String(index + 1).padStart(2, '0')}</div><div class="rule-content"><strong>{config.mode === 'select' ? 'Inclure les questions' : 'Exclure les questions'}</strong><div class="criteria"><span>{ruleTags(config)}</span><b>{config.join === 'and' ? 'ET' : 'OU'}</b><span>{ruleLevels(config)}</span></div></div><button class="delete-rule" type="button" aria-label={`Supprimer la règle ${index + 1}`} disabled={removingRuleId === config.id} onclick={() => void removeConfig(config.id)}>{removingRuleId === config.id ? 'Suppression…' : 'Supprimer'}</button></article>{:else}<div class="rules-empty"><strong>Aucune règle d’inclusion</strong><p>Ajoutez une règle pour calculer les questions éligibles.</p></div>{/each}</div>
			{#if ruleError}<p class="rule-error" role="alert">{ruleError}</p>{/if}
			</div>{/if}
		</section>

		<section class="question-pool" aria-labelledby="pool-title">
			<div class="pool-heading"><div><p class="eyebrow">Étape 2 · Sélection</p><h2 id="pool-title">Questions de l’épisode</h2><p>Recherchez parmi les questions éligibles, puis retenez celles qui seront disponibles pour la grille.</p></div><div class="pool-counts"><span><strong>{questionPage?.eligible_count ?? 0}</strong> éligibles</span><span class="selected-count"><strong>{questionPage?.selected_count ?? 0}</strong> retenues</span></div></div>
			<form class="question-filters" onsubmit={(event) => { event.preventDefault(); void loadQuestions(1); }}><label for="question-search"><span>Rechercher</span><input id="question-search" bind:value={search} type="search" placeholder="Question ou tag" /></label><label for="question-level"><span>Niveau</span><select id="question-level" bind:value={filterLevel}><option value="all">Tous les niveaux</option>{#each [1,2,3,4,5] as level}<option value={String(level)}>Niveau {level}</option>{/each}</select></label><button>Rechercher</button></form>
			{#if questionPage?.eligible_count}
				<div class="question-list" aria-live="polite">{#each questionPage.results as question}<article class:selected={question.is_selected}><button class="selection-toggle" type="button" aria-label={`${question.is_selected ? 'Retirer' : 'Sélectionner'} ${question.question}`} disabled={pendingQuestionId === question.id} onclick={() => void toggleQuestion(question.id, question.is_selected)}><span aria-hidden="true">{question.is_selected ? '✓' : '+'}</span></button><div class="question-copy"><strong>{question.question}</strong><small>{question.tags.join(' · ') || 'Sans tag'}</small></div><span class="level">Niv. {question.level}</span><span class="status">{question.is_selected ? 'Retenue' : 'Disponible'}</span></article>{:else}<p class="empty">Aucune question ne correspond aux filtres de recherche.</p>{/each}</div>
				{#if questionPage.next || questionPage.previous}<nav class="pagination" aria-label="Pagination des questions"><button type="button" disabled={!questionPage.previous} onclick={() => void loadQuestions(currentPage - 1)}>Précédent</button><span>Page {currentPage}</span><button type="button" disabled={!questionPage.next} onclick={() => void loadQuestions(currentPage + 1)}>Suivant</button></nav>{/if}
			{:else}<div class="pool-empty"><strong>{configs.length ? 'Aucune question ne correspond aux règles.' : 'Le pool attend ses règles.'}</strong><p>{configs.length ? 'Modifiez vos critères pour rendre des questions éligibles.' : 'Commencez par une règle « Inclure » ci-dessus.'}</p></div>{/if}
			{#if questionError}<p class="rule-error" role="alert">{questionError}</p>{/if}
		</section>
		{#if errorMessage}<p class="rule-error" role="alert">{errorMessage}</p>{/if}
	{:else}<p class="rule-error">{errorMessage}</p>{/if}
</main>

<style>
	:global(*){box-sizing:border-box}:global(html),:global(body){margin:0;background:#0f172a;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,sans-serif}main{width:min(100%,72rem);min-height:100dvh;margin:auto;padding:clamp(1.25rem,4vw,3rem)}a{color:#c4b5fd;font-size:.85rem;font-weight:750;text-decoration:none}.loading{margin-top:5rem;color:#cbd5e1;text-align:center}header{display:flex;align-items:end;gap:1rem;margin:3rem 0 2rem}header p{margin:0 auto 0 0;color:#94a3b8;font-size:.85rem}h1{margin:0;color:#f8fafc;font-size:clamp(2.5rem,6vw,4.5rem);letter-spacing:-.07em}header span{color:#cbd5e1}.rules,.question-pool{margin-bottom:1.5rem;border:1px solid #334155;border-radius:1rem;padding:clamp(1rem,3vw,1.5rem);background:#1e293b}.rules-heading,.pool-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:1.25rem}.rules.collapsed .rules-heading{margin-bottom:0}.rules-controls{display:flex;align-items:center;gap:.5rem}.eyebrow{margin:0 0 .35rem;color:#c4b5fd;font-size:.68rem;font-weight:850;letter-spacing:.11em;text-transform:uppercase}.rules h2,.question-pool h2{margin:0;color:#f8fafc;font-size:1.35rem;letter-spacing:-.035em}.rules-heading>div>p:last-child,.pool-heading>div>p:last-child{max-width:42rem;margin:.45rem 0 0;color:#cbd5e1;font-size:.84rem;line-height:1.55}.rule-count{flex:none;border:1px solid rgba(124,58,237,.5);border-radius:999px;padding:.4rem .65rem;background:rgba(124,58,237,.12);color:#ddd6fe;font-size:.72rem;font-weight:800}.rules-toggle{display:inline-flex;align-items:center;gap:.35rem;min-height:2.4rem;border:1px solid #475569;border-radius:.55rem;padding:.45rem .65rem;background:transparent;color:#cbd5e1;cursor:pointer;font:inherit;font-size:.74rem;font-weight:800}.rules-toggle:hover{border-color:#a78bfa;color:#f8fafc}.rules-toggle svg{width:1rem;height:1rem;fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.7;transition:transform .18s ease}.rules-toggle[aria-expanded="true"] svg{transform:rotate(180deg)}.rules-toggle:focus-visible{outline:3px solid #a78bfa;outline-offset:3px}.rule-builder{border:1px solid #475569;border-radius:.8rem;padding:1rem;background:#17213a}.builder-heading{display:flex;align-items:baseline;justify-content:space-between;gap:1rem;margin-bottom:.9rem}.builder-heading strong{font-size:.9rem}.builder-heading span{color:#94a3b8;font-size:.74rem}.rule-fields{display:grid;grid-template-columns:1.1fr 1.25fr minmax(10rem,1.4fr) 9rem;gap:.75rem}.rule-fields label,.question-filters label{display:block;color:#cbd5e1;font-size:.73rem;font-weight:750}.rule-fields label span,.question-filters label span{display:block;margin-bottom:.38rem}.rule-fields input,.rule-fields select,.question-filters input,.question-filters select{width:100%;min-height:2.8rem;border:1px solid #475569;border-radius:.55rem;padding:0 .7rem;background:#0f172a;color:#f8fafc;font:inherit;font-size:.84rem}.rule-fields input::placeholder,.question-filters input::placeholder{color:#94a3b8;opacity:1}.rule-fields input:focus,.rule-fields select:focus,.question-filters input:focus,.question-filters select:focus{border-color:#a78bfa;outline:3px solid rgba(167,139,250,.24)}.builder-actions{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-top:1rem;border-top:1px solid #334155;padding-top:1rem}.builder-actions p{margin:0;color:#94a3b8;font-size:.74rem}.builder-actions p strong{color:#ddd6fe}.builder-actions button,.question-filters button{min-height:2.8rem;flex:none;border:0;border-radius:.6rem;padding:.65rem 1rem;background:#7c3aed;color:white;cursor:pointer;font:inherit;font-size:.82rem;font-weight:800}.builder-actions button:hover,.question-filters button:hover{background:#8b5cf6}.builder-actions button:disabled,.delete-rule:disabled,.selection-toggle:disabled,.pagination button:disabled{cursor:not-allowed;opacity:.55}.active-rules{margin-top:1.25rem}.active-rules-heading{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:.65rem}.active-rules-heading h3{margin:0;color:#f8fafc;font-size:.86rem}.active-rules-heading span{color:#94a3b8;font-size:.72rem}.rule-card{display:grid;grid-template-columns:2.5rem minmax(0,1fr) auto;gap:.8rem;align-items:center;border-top:1px solid #334155;padding:.85rem 0}.rule-index{display:grid;width:2rem;height:2rem;place-items:center;border-radius:.5rem;background:rgba(34,197,94,.12);color:#86efac;font-size:.68rem;font-weight:850}.rule-card.exclude .rule-index{background:rgba(239,68,68,.12);color:#fca5a5}.rule-content strong{display:block;color:#f8fafc;font-size:.84rem}.criteria{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem;margin-top:.35rem}.criteria span{border-radius:999px;padding:.24rem .45rem;background:#334155;color:#cbd5e1;font-size:.69rem;line-height:1.2}.criteria b{color:#a78bfa;font-size:.64rem;letter-spacing:.07em}.delete-rule{min-height:2.5rem;border:1px solid transparent;border-radius:.55rem;padding:.5rem .65rem;background:transparent;color:#fca5a5;cursor:pointer;font:inherit;font-size:.75rem;font-weight:750}.delete-rule:hover{border-color:rgba(239,68,68,.5);background:rgba(239,68,68,.1)}.rules-empty,.pool-empty{border:1px dashed #475569;border-radius:.7rem;padding:1rem;background:rgba(15,23,42,.45)}.rules-empty strong,.pool-empty strong{font-size:.82rem}.rules-empty p,.pool-empty p{margin:.35rem 0 0;color:#94a3b8;font-size:.78rem;line-height:1.45}.pool-counts{display:flex;gap:.6rem}.pool-counts span{display:grid;gap:.1rem;border:1px solid #475569;border-radius:.65rem;padding:.55rem .7rem;background:#0f172a;color:#94a3b8;font-size:.66rem;font-weight:750;text-align:right}.pool-counts strong{color:#7dd3fc;font-size:1.1rem;font-variant-numeric:tabular-nums}.pool-counts .selected-count{border-color:rgba(124,58,237,.6)}.pool-counts .selected-count strong{color:#c4b5fd}.question-filters{display:grid;grid-template-columns:minmax(0,1fr) 10rem auto;gap:.75rem;align-items:end;margin-bottom:1rem;border-bottom:1px solid #334155;padding-bottom:1rem}.question-list{border:1px solid #334155;border-radius:.8rem;overflow:hidden;background:#17213a}.question-list article{display:grid;grid-template-columns:2.5rem minmax(0,1fr) 4.5rem 5.5rem;gap:.75rem;align-items:center;border-top:1px solid #334155;padding:.8rem}.question-list article:first-child{border-top:0}.question-list article.selected{background:rgba(124,58,237,.09)}.selection-toggle{display:grid;width:2.35rem;height:2.35rem;place-items:center;border:1px solid #475569;border-radius:.6rem;background:#0f172a;color:#cbd5e1;cursor:pointer;font:inherit;font-size:1rem;font-weight:850}.selected .selection-toggle{border-color:#7c3aed;background:#7c3aed;color:#fff}.question-copy strong,.question-copy small{display:block}.question-copy strong{font-size:.86rem}.question-copy small{margin-top:.25rem;color:#94a3b8;font-size:.72rem}.level,.status{font-size:.72rem;font-weight:750;text-align:right}.level{color:#7dd3fc}.status{color:#94a3b8}.selected .status{color:#c4b5fd}.pagination{display:flex;align-items:center;justify-content:flex-end;gap:.75rem;margin-top:1rem}.pagination button{min-height:2.55rem;border:1px solid #475569;border-radius:.55rem;padding:.5rem .75rem;background:transparent;color:#cbd5e1;cursor:pointer;font:inherit;font-size:.78rem;font-weight:750}.pagination span{color:#94a3b8;font-size:.75rem}.rule-error{margin:1rem 0 0;color:#fecaca;font-size:.8rem}@media(max-width:820px){.rule-fields{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){header,.rules-heading,.pool-heading,.builder-heading,.builder-actions{align-items:stretch;flex-direction:column}.rules-controls{justify-content:space-between}.rule-count{align-self:flex-start}.rule-fields,.question-filters{grid-template-columns:1fr}.builder-actions button,.question-filters button{width:100%}.rule-card{grid-template-columns:2.5rem minmax(0,1fr)}.delete-rule{grid-column:2;justify-self:start;margin-top:-.3rem}.pool-counts{align-self:stretch}.pool-counts span{flex:1;text-align:left}.question-list article{grid-template-columns:2.5rem minmax(0,1fr)}.level,.status{grid-column:2;text-align:left}.level{margin-top:-.35rem}.status{display:none}.pagination{justify-content:space-between}}@media(prefers-reduced-motion:reduce){*{transition-duration:.01ms!important}}
</style>
