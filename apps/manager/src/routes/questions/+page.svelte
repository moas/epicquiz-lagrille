<script lang="ts">
	import { onMount } from 'svelte';
	import { deleteQuestion, getQuestionPage, importQuestions, type Question } from '$lib/episodes-api';

	let questions = $state<Question[]>([]);
	let search = $state('');
	let selectedLevel = $state('all');
	let appliedSearch = $state('');
	let appliedLevel = $state('all');
	let page = $state(1);
	let count = $state(0);
	let hasNext = $state(false);
	let hasPrevious = $state(false);
	let isLoading = $state(true);
	let isImporting = $state(false);
	let error = $state('');
	let notice = $state('');
	let fileInput: HTMLInputElement;

	const hasFilters = $derived(Boolean(appliedSearch || appliedLevel !== 'all'));

	async function load() {
		isLoading = true;
		error = '';
		const parameters = new URLSearchParams({ page: String(page) });
		if (appliedSearch) parameters.set('search', appliedSearch);
		if (appliedLevel !== 'all') parameters.set('level', appliedLevel);

		try {
			const result = await getQuestionPage(parameters);
			questions = result.results;
			count = result.count;
			hasNext = Boolean(result.next);
			hasPrevious = Boolean(result.previous);
		} catch {
			error = 'Impossible de charger la bibliothèque.';
		} finally {
			isLoading = false;
		}
	}

	function applyFilters() {
		page = 1;
		appliedSearch = search.trim();
		appliedLevel = selectedLevel;
		void load();
	}

	function changePage(nextPage: number) {
		page = nextPage;
		void load();
	}

	async function remove(question: Question) {
		if (!confirm(`Supprimer définitivement « ${question.question} » ?`)) return;
		error = '';
		try {
			await deleteQuestion(question.id);
			if (questions.length === 1 && page > 1) page -= 1;
			await load();
			notice = 'La question a été supprimée.';
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Impossible de supprimer cette question.';
		}
	}

	onMount(() => { void load(); });

	async function upload(file: File | undefined) {
		if (!file) return;
		isImporting = true;
		error = '';
		notice = '';
		try {
			const result = await importQuestions(file);
			page = 1;
			await load();
			notice = `${result.imported_questions} question(s) importée(s).`;
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Impossible d’importer ce fichier.';
		} finally {
			isImporting = false;
			fileInput.value = '';
		}
	}
</script>

<main>
	<a class="back" href="/">← Retour aux épisodes</a>
	<header>
		<div class="header-title"><p class="eyebrow">Base de connaissance</p><h1>Bibliothèque de questions</h1><p>Explorez et organisez les questions disponibles pour vos épisodes.</p></div>
		<div class="actions"><a class="primary-action" href="/questions/new">Ajouter une question</a><input bind:this={fileInput} id="yaml-upload" type="file" accept=".yaml,.yml" onchange={(event) => void upload(event.currentTarget.files?.[0])} /><button type="button" class="secondary" disabled={isImporting} onclick={() => fileInput.click()}>{isImporting ? 'Import en cours…' : 'Importer un YAML'}</button></div>
	</header>
	{#if notice}<p class="notice" role="status">{notice}</p>{/if}
	{#if isLoading}<section class="loading">Chargement de la bibliothèque…</section>
	{:else if error}<section class="error" role="alert">{error}</section>
	{:else}
		<form class="filters" onsubmit={(event) => { event.preventDefault(); applyFilters(); }}>
			<label><span>Recherche</span><input bind:value={search} type="search" placeholder="Titre, mot-clé…" /></label>
			<label><span>Niveau</span><select bind:value={selectedLevel}><option value="all">Tous les niveaux</option>{#each [1, 2, 3, 4, 5] as level}<option value={String(level)}>Niveau {level}</option>{/each}</select></label>
			<button type="submit">Rechercher</button>
			<p><strong>{count}</strong> questions</p>
		</form>
		{#if questions.length}
			<section class="question-list">
				{#each questions as question}
					<article>
						<div class="question-copy"><strong>{question.question}</strong><small>{question.tags.join(' · ') || 'Sans tag'}</small></div>
						<span class="level">Niveau {question.level}</span>
						<span class:inactive={!question.is_active} class="availability">{question.is_active ? 'Disponible' : 'Inactive'}</span>
						<div class="row-actions"><a class="icon-action" href={`/questions/${question.id}`} aria-label={`Voir ${question.question}`}>Voir</a><a class="icon-action" href={`/questions/${question.id}/edit`} aria-label={`Modifier ${question.question}`}>Modifier</a><button type="button" class="icon-action danger" aria-label={`Supprimer ${question.question}`} onclick={() => void remove(question)}>Supprimer</button></div>
					</article>
				{/each}
			</section>
			<nav class="pagination"><button class="secondary" disabled={!hasPrevious} onclick={() => changePage(page - 1)}>← Précédent</button><p>Page <strong>{page}</strong></p><button disabled={!hasNext} onclick={() => changePage(page + 1)}>Suivant →</button></nav>
		{:else if hasFilters}<section class="empty"><strong>Aucune question ne correspond à ces critères.</strong><p>Modifiez la recherche ou réinitialisez le niveau.</p></section>
		{:else}<section class="empty"><strong>La bibliothèque est vide.</strong><p>Importez un fichier YAML ou ajoutez votre première question.</p></section>{/if}
	{/if}
</main>

<style>
	:global(body){margin:0;background:#0f172a;color:#f8fafc;font-family:Inter,system-ui,sans-serif}main{max-width:76rem;margin:auto;padding:3rem}.back{color:#c4b5fd;font-weight:700;text-decoration:none}header{display:grid;gap:0;margin:3rem 0 2rem}.header-title{width:100%}h1{margin:.4rem 0;white-space:nowrap;font-size:clamp(2.5rem,6vw,4.5rem);letter-spacing:-.07em}.eyebrow{margin:0;color:#c4b5fd;font-size:.72rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}header p:last-child{color:#cbd5e1}.actions{display:flex;width:100%;gap:.7rem;align-items:flex-end;justify-content:flex-end}.actions input{display:none}button,.primary-action{min-height:2.8rem;border:0;border-radius:.6rem;padding:.65rem 1rem;background:#7c3aed;color:#fff;cursor:pointer;font:inherit;font-weight:750;text-decoration:none}.primary-action{display:inline-flex;align-items:center;justify-content:center}.actions>.primary-action{box-sizing:border-box;width:13.5rem;justify-content:center}.actions>.secondary{box-sizing:border-box;width:11.5rem;justify-content:center}.secondary{border:1px solid #475569;background:#1e293b;color:#ddd6fe}.filters{display:grid;grid-template-columns:minmax(0,1fr) 12rem auto auto;gap:.8rem;align-items:end;margin-bottom:1rem;border:1px solid #334155;border-radius:1rem;padding:1rem;background:#17213a}.filters label span{display:block;margin-bottom:.4rem;color:#94a3b8;font-size:.72rem;font-weight:800}.filters input,.filters select{width:100%;min-height:2.7rem;border:1px solid #475569;border-radius:.55rem;padding:0 .7rem;background:#1e293b;color:#f8fafc;font:inherit}.filters p{margin:0 0 .7rem;color:#cbd5e1;white-space:nowrap}.question-list{overflow:hidden;border:1px solid #334155;border-radius:1rem;background:#1e293b}.question-list article{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:1rem;align-items:center;border-top:1px solid #334155;padding:1.1rem 1.25rem}.question-list article:first-child{border-top:0}.question-copy strong,.question-copy small{display:block}.question-copy small{margin-top:.35rem;color:#94a3b8;font-size:.76rem}.level,.availability{border-radius:999px;padding:.35rem .6rem;background:rgba(124,58,237,.18);color:#ddd6fe;font-size:.75rem;font-weight:750}.availability{background:rgba(34,197,94,.12);color:#86efac}.availability.inactive{background:#334155;color:#cbd5e1}.row-actions{display:flex;gap:.45rem}.icon-action{display:inline-flex;align-items:center;justify-content:center;min-height:2.25rem;border:0;border-radius:.45rem;padding:.4rem .55rem;background:#334155;color:#f8fafc;cursor:pointer;font:inherit;font-size:.72rem;font-weight:750;text-decoration:none}.icon-action.danger{border:1px solid rgba(239,68,68,.55);background:transparent;color:#fca5a5}.pagination{display:flex;justify-content:center;align-items:center;gap:1rem;margin-top:1.5rem}.pagination p{color:#cbd5e1}.pagination button:disabled{opacity:.45;cursor:not-allowed}.notice,.loading,.error,.empty{border:1px solid #334155;border-radius:.8rem;padding:1rem;background:#17213a}.notice{border-color:rgba(34,197,94,.5);color:#bbf7d0}.error{border-color:rgba(239,68,68,.5);color:#fecaca}.empty{color:#cbd5e1;text-align:center}@media(max-width:700px){main{padding:1.25rem}h1{white-space:normal;font-size:clamp(2rem,10vw,3rem)}.actions{flex-direction:column}.actions button,.actions .primary-action{width:100%}.filters{grid-template-columns:1fr}.filters button{width:100%}.filters p{margin:0}.question-list article{grid-template-columns:1fr}.level,.availability{justify-self:start}.row-actions{width:100%;flex-wrap:wrap}.row-actions .icon-action{flex:1}}
</style>
