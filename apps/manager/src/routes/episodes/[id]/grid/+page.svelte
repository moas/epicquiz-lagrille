<script lang="ts">
	import { onMount } from 'svelte';
	import GridConfigurationDialog from '$lib/GridConfigurationDialog.svelte';
	import RandomDispatchDialog from '$lib/RandomDispatchDialog.svelte';
	import {
		deletePreparedGrid,
		getEpisode,
		getEpisodeQuestions,
		getPreparedGrid,
		getPrizeAttributes,
		getSpecialAttributesSummary,
		getSelectedEpisodeQuestions,
		getStealAttributes,
		gridLabel,
		type Episode,
		type PreparedGrid,
		type Question,
		type SpecialAttribute
	} from '$lib/episodes-api';
	import type { PageProps } from './$types';

	let { params }: PageProps = $props();
	let episode = $state<Episode | null>(null);
	let selectedQuestionsByLevel = $state<Record<string, number>>({});
	let isLoading = $state(true);
	let isEditing = $state(false);
	let errorMessage = $state('');
	let notice = $state('');
	let preparedGrid = $state<PreparedGrid | null>(null);
	let selectedQuestions = $state<Question[]>([]);
	let specialAttributes = $state<SpecialAttribute[]>([]);
	let isDispatchingChallenges = $state(false);
	let isDispatchingAttributes = $state(false);
	let isDeletingGrid = $state(false);

	const expectedQuestionCount = $derived(episode?.metadata.grid_config ? episode.metadata.grid_config.rows * episode.metadata.grid_config.columns - episode.metadata.grid_config.empty_cell_count : 0);
	const levelRequirements = $derived.by(() => {
		const grid = episode?.metadata.grid_config;
		if (!grid) return [];
		return Array.from({ length: 5 }, (_, index) => {
			const level = String(index + 1);
			const expected = Number(grid.point_distribution[level] ?? 0);
			const selected = selectedQuestionsByLevel[level] ?? 0;
			return { level, expected, selected, gap: expected - selected };
		});
	});
	const missingLevelRequirements = $derived(levelRequirements.filter((requirement) => requirement.gap > 0));
	const canDispatchChallenges = $derived(expectedQuestionCount > 0 && missingLevelRequirements.length === 0);
	let activeAttributeCount = $state(0);
	const challengesSaved = $derived(preparedGrid?.state === 'positions_drawn' || preparedGrid?.state === 'attributes_drawn');
	const attributesSaved = $derived(preparedGrid?.state === 'attributes_drawn');
	const attributeCapacity = $derived((preparedGrid?.cells.filter((cell) => cell.challenge_id).length ?? 0) * (episode?.metadata.grid_config?.max_attrs_per_cell ?? 1));
	const canDispatchAttributes = $derived(challengesSaved && activeAttributeCount <= attributeCapacity);

	async function restartGrid() {
		if (!confirm('Supprimer la grille verrouillée ? Les challenges, lots et attributs de cette grille seront supprimés.')) return;
		isDeletingGrid = true;
		try {
			await deletePreparedGrid(params.id);
			preparedGrid = null;
			specialAttributes = [];
			episode = await getEpisode(params.id);
			notice = 'La grille a été supprimée. Vous pouvez reprendre toute sa préparation.';
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Impossible de supprimer la grille.';
		} finally {
			isDeletingGrid = false;
		}
	}

	async function loadAttributeSummary() {
		try {
			activeAttributeCount = (await getSpecialAttributesSummary(params.id)).active_count;
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Impossible de charger le nombre d’attributs spéciaux.';
		}
	}

	onMount(async () => {
		try {
			const [loadedEpisode, questionPool, questions, attributes, attributesSummary] = await Promise.all([
				getEpisode(params.id),
				getEpisodeQuestions(params.id),
				getSelectedEpisodeQuestions(params.id),
				Promise.all([getStealAttributes(params.id), getPrizeAttributes(params.id)]),
				getSpecialAttributesSummary(params.id)
			]);
			episode = loadedEpisode;
			selectedQuestionsByLevel = questionPool.selected_by_level;
			selectedQuestions = questions;
			specialAttributes = attributes.flat();
			activeAttributeCount = attributesSummary.active_count;
			try { preparedGrid = await getPreparedGrid(params.id); } catch { preparedGrid = null; }
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Impossible de charger la grille.';
		} finally {
			isLoading = false;
		}
	});
</script>

<main>
	<a href={`/episodes/${params.id}`}>← Retour à l’épisode</a>
	{#if isLoading}<p>Chargement…</p>
	{:else if episode}
		<header><div><p>Épisode · {episode.title}</p><h1>Grille</h1><span>{gridLabel(episode)}</span></div>{#if challengesSaved}<button class="danger" disabled={isDeletingGrid} onclick={() => void restartGrid()}>{isDeletingGrid ? 'Suppression…' : 'Supprimer la grille et recommencer'}</button>{:else}<button onclick={() => isEditing = true}>{episode.metadata.grid_config ? 'Modifier la configuration' : 'Configurer la grille'}</button>{/if}</header>
		{#if episode.metadata.grid_config}
			<section class="preview" style={`--columns:${episode.metadata.grid_config.columns}`} aria-label="Aperçu de la grille">{#each Array(episode.metadata.grid_config.rows * episode.metadata.grid_config.columns) as _, index}{@const cell = preparedGrid?.cells[index]}<span class:challenge={Boolean(cell?.challenge_id)} class:empty={preparedGrid && !cell?.challenge_id}>{cell?.name ?? index + 1}</span>{/each}</section>
			<section class="configuration-cards" aria-label="Préparer les contenus de la grille">
				<article class="configuration-card featured" class:blocked={!canDispatchChallenges && !challengesSaved}><span class="card-number">01</span><p class="eyebrow">Questions de la grille</p><h2>Challenges</h2><p>Associez les questions aux cases, prévisualisez un tirage aléatoire puis confirmez la répartition.</p>{#if challengesSaved}<div class="pool-status ready" role="status"><strong>Challenges enregistrés</strong><span>{preparedGrid?.cells.filter((cell) => cell.challenge_id).length} cases contiennent une question. Le tirage est verrouillé.</span></div>{:else}<div class:ready={canDispatchChallenges} class="pool-status" role="status">{#if canDispatchChallenges}<strong>Contrat de grille couvert</strong><span>Les questions en surplus restent disponibles pour le tirage aléatoire.</span>{:else}<strong>Questions manquantes</strong><span>Complétez uniquement les niveaux suivants pour pouvoir lancer le tirage.</span><ul class="level-checks">{#each missingLevelRequirements as requirement}<li><b>Niv. {requirement.level}</b><span>{requirement.selected} / {requirement.expected}</span><em>manque {requirement.gap}</em></li>{/each}</ul>{/if}</div><button type="button" disabled={!canDispatchChallenges} onclick={() => isDispatchingChallenges = true}>{canDispatchChallenges ? 'Prévisualiser le tirage' : 'Configuration à compléter'} <span aria-hidden="true">→</span></button>{/if}</article>
				<article class="configuration-card" class:blocked={challengesSaved && !attributesSaved && !canDispatchAttributes}><span class="card-number">02</span><p class="eyebrow">Lots et mécaniques</p><h2>Attributs spéciaux</h2><p>Attribuez aléatoirement les lots et les vols définis dans la configuration de la grille.</p><div class:ready={canDispatchAttributes || attributesSaved} class="attribute-status"><strong>{attributesSaved ? 'Attributs enregistrés' : `${activeAttributeCount} attribut${activeAttributeCount === 1 ? '' : 's'} actif${activeAttributeCount === 1 ? '' : 's'}`}</strong><span>{attributesSaved ? 'Le tirage est verrouillé.' : challengesSaved && !canDispatchAttributes ? `${activeAttributeCount} attributs pour ${attributeCapacity} emplacements : augmentez le maximum par case.` : challengesSaved && activeAttributeCount > 0 ? `${attributeCapacity} emplacements disponibles pour le tirage.` : challengesSaved ? 'Aucun attribut requis : vous pouvez verrouiller les cases.' : 'Disponible après la répartition des challenges.'}</span></div>{#if !attributesSaved}<button type="button" disabled={!canDispatchAttributes} onclick={() => isDispatchingAttributes = true}>{activeAttributeCount > 0 ? 'Prévisualiser le tirage' : 'Finaliser sans attribut'} <span aria-hidden="true">→</span></button>{/if}</article>
			</section>
			{#if notice}<p class="notice" role="status">{notice}</p>{/if}
			<section class="details"><div><small>Cases vides</small><strong>{episode.metadata.grid_config.empty_cell_count}</strong></div><div><small>Attributs max. / case</small><strong>{episode.metadata.grid_config.max_attrs_per_cell ?? 1}</strong></div>{#each Object.entries(episode.metadata.grid_config.point_distribution) as [points, count]}<div><small>{points} points</small><strong>{count} cases</strong></div>{/each}</section>
		{:else}<section class="empty"><h2>La grille n’est pas encore configurée</h2><p>Définissez ses dimensions et la répartition des points pour continuer.</p></section>{/if}
		{#if isEditing}<GridConfigurationDialog {episode} configurationLocked={challengesSaved} onclose={() => isEditing = false} onconfigured={(updated) => { episode = updated; isEditing = false; }} />{/if}
		{#if isDispatchingChallenges && episode.metadata.grid_config}<RandomDispatchDialog episodeId={params.id} config={episode.metadata.grid_config} mode="challenges" questions={selectedQuestions} onclose={() => isDispatchingChallenges = false} onsaved={(grid) => { preparedGrid = grid; isDispatchingChallenges = false; notice = 'La répartition des challenges est enregistrée.'; }} />{/if}
		{#if isDispatchingAttributes && episode.metadata.grid_config}<RandomDispatchDialog episodeId={params.id} config={episode.metadata.grid_config} mode="attributes" attributes={specialAttributes} cells={preparedGrid?.cells ?? []} onclose={() => isDispatchingAttributes = false} onsaved={(grid) => { preparedGrid = grid; isDispatchingAttributes = false; notice = 'L’attribution des attributs spéciaux est enregistrée.'; }} />{/if}
	{:else}<p class="error">{errorMessage}</p>{/if}
</main>

<style>
	:global(*){box-sizing:border-box}:global(html),:global(body){margin:0;background:#0f172a;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,sans-serif}main{width:min(100%,72rem);min-height:100dvh;margin:auto;padding:clamp(1.25rem,4vw,3rem)}a{color:#c4b5fd;font-size:.85rem;font-weight:750;text-decoration:none}header{display:flex;justify-content:space-between;gap:1rem;margin:3rem 0 2rem}header p,small{color:#94a3b8}h1{margin:.3rem 0;color:#f8fafc;font-size:clamp(2.5rem,6vw,4.5rem);letter-spacing:-.07em}h2{margin:.25rem 0;color:#f8fafc;font-size:1.1rem}header span{color:#cbd5e1}button{min-height:2.8rem;align-self:end;border:0;border-radius:.6rem;padding:.65rem 1rem;background:#7c3aed;color:white;cursor:pointer;font:inherit;font-weight:750}header .danger{border:1px solid rgba(239,68,68,.65);background:rgba(239,68,68,.1);color:#fecaca}header .danger:hover{background:rgba(239,68,68,.17);color:#fff}.preview{display:grid;grid-template-columns:repeat(var(--columns),minmax(0,1fr));gap:.5rem;border:1px solid #334155;border-radius:1rem;padding:1rem;background:#1e293b}.preview span{display:grid;min-height:4rem;place-items:center;border:1px solid #475569;border-radius:.55rem;background:#0f172a;color:#c4b5fd;font-weight:750}.preview span.challenge{border-color:rgba(124,58,237,.72);background:rgba(124,58,237,.18);color:#ddd6fe}.preview span.empty{border-style:dashed;color:#64748b}.configuration-cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1rem}.configuration-card{display:flex;min-height:16rem;flex-direction:column;align-items:flex-start;border:1px solid #334155;border-radius:.9rem;padding:1.25rem;background:#1e293b}.configuration-card.featured{border-color:rgba(124,58,237,.65);background:linear-gradient(150deg,rgba(124,58,237,.18),#1e293b 46%)}.configuration-card.blocked{border-color:rgba(245,158,11,.52);background:linear-gradient(150deg,rgba(245,158,11,.1),#1e293b 46%)}.card-number{margin-bottom:auto;color:#a78bfa;font-size:.72rem;font-weight:850;letter-spacing:.1em}.eyebrow{margin:0!important;color:#c4b5fd!important;font-size:.68rem!important;font-weight:800;letter-spacing:.1em;text-transform:uppercase}.configuration-card h2{margin:.4rem 0;color:#f8fafc;font-size:1.1rem}.configuration-card>p:not(.eyebrow){margin:.25rem 0 .8rem;color:#cbd5e1;font-size:.82rem;line-height:1.55}.pool-status,.attribute-status{width:100%;margin-bottom:1rem;border:1px solid rgba(245,158,11,.45);border-radius:.6rem;padding:.65rem .7rem;background:rgba(245,158,11,.09);color:#fde68a;font-size:.72rem;line-height:1.4}.pool-status.ready,.attribute-status.ready{border-color:rgba(34,197,94,.45);background:rgba(34,197,94,.09);color:#bbf7d0}.pool-status strong,.pool-status span,.attribute-status strong,.attribute-status span{display:block}.pool-status span,.attribute-status span{margin-top:.2rem}.level-checks{display:grid;gap:.3rem;margin:.6rem 0;padding:0;list-style:none}.level-checks li{display:grid;grid-template-columns:2.6rem 1fr auto;gap:.35rem;align-items:center;border-radius:.35rem;padding:.2rem .35rem;background:rgba(15,23,42,.45);font-variant-numeric:tabular-nums}.level-checks li em{font-style:normal;font-size:.66rem}.configuration-card button{margin-top:auto;align-self:stretch;font-size:.8rem;text-align:left}.configuration-card button span{float:right}.configuration-card button:disabled{cursor:not-allowed;opacity:.5}.notice{margin:1rem 0 0;border:1px solid rgba(56,189,248,.45);border-radius:.65rem;padding:.75rem 1rem;background:rgba(56,189,248,.08);color:#bae6fd;font-size:.82rem}.details{display:flex;flex-wrap:wrap;gap:1rem;margin-top:1rem}.details div,.empty{border:1px solid #334155;border-radius:.75rem;padding:1rem;background:#1e293b}.details strong{display:block;margin-top:.35rem}.empty{margin-top:1rem}.empty p{color:#cbd5e1}.error{color:#fecaca}@media(max-width:820px){.configuration-cards{grid-template-columns:1fr}.configuration-card{min-height:0}}@media(max-width:600px){header{flex-direction:column;align-items:stretch}button{align-self:stretch}.preview{gap:.3rem;padding:.5rem}.preview span{min-height:2.4rem;font-size:.72rem}}
</style>
