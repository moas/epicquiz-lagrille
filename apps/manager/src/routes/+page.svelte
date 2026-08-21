<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	import { episodeStateLabel, getEpisodes, gridLabel, type Episode, type EpisodeState } from '$lib/episodes-api';
	import { logout } from '$lib/auth';
	import CreateEpisodeDialog from '$lib/CreateEpisodeDialog.svelte';

	const states: { label: string; value: EpisodeState | null }[] = [
		{ label: 'Tous', value: null },
		{ label: 'À préparer', value: 'pending' },
		{ label: 'En cours', value: 'start' },
		{ label: 'Terminés', value: 'end' }
	];

	let episodes = $state<Episode[]>([]);
	let count = $state(0);
	let isLoading = $state(true);
	let errorMessage = $state('');
	let searchValue = $state('');
	let isClient = $state(false);
	let isCreateDialogOpen = $state(false);
	let searchInput: HTMLInputElement;

	const selectedState = $derived((page.url.searchParams.get('state') as EpisodeState | null) ?? null);
	const currentPage = $derived(Math.max(1, Number(page.url.searchParams.get('page') ?? '1')));
	const totalPages = $derived(Math.max(1, Math.ceil(count / 12)));

	function updateQuery(changes: Record<string, string | null>) {
		const parameters = new URLSearchParams(page.url.searchParams);
		for (const [key, value] of Object.entries(changes)) {
			if (value) parameters.set(key, value);
			else parameters.delete(key);
		}
		void goto(parameters.size ? `/?${parameters}` : '/', { keepFocus: true, noScroll: true });
	}

	function submitSearch() {
		updateQuery({ search: searchValue.trim() || null, page: null });
	}

	async function loadEpisodes() {
		isLoading = true;
		errorMessage = '';
		const parameters = new URLSearchParams({ page: String(currentPage), page_size: '12' });
		if (selectedState) parameters.set('state', selectedState);
		const search = page.url.searchParams.get('search');
		if (search) parameters.set('search', search);

		try {
			const response = await getEpisodes(parameters);
			episodes = response.results;
			count = response.count;
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Impossible de charger les épisodes.';
			episodes = [];
			count = 0;
		} finally {
			isLoading = false;
		}
	}

	$effect(() => {
		if (!isClient) return;
		searchValue = page.url.searchParams.get('search') ?? '';
		void loadEpisodes();
	});

	onMount(() => {
		isClient = true;
		searchInput?.focus();
	});

	function handleEpisodeCreated(episode: Episode) {
		isCreateDialogOpen = false;
		void goto(`/episodes/${episode.id}`);
	}

</script>

<svelte:head>
	<title>Épisodes · EpicQuiz - La Grille</title>
	<meta name="description" content="Liste des épisodes à gérer dans EpicQuiz - La Grille." />
</svelte:head>

<main id="content">
	<header class="topbar">
		<a class="brand" href="/" aria-label="EpicQuiz - La Grille, liste des épisodes"><img src="/brand-icon.png" alt="" /><span>La Grille</span></a>
		<div class="topbar-actions"><button type="button" class="logout-button" onclick={logout}>Déconnexion</button><button type="button" class="primary-action" onclick={() => isCreateDialogOpen = true}>Créer un épisode</button></div>
	</header>

	<section class="intro" aria-labelledby="page-title"><p class="eyebrow">Espace manager</p><h1 id="page-title">Vos épisodes</h1><p>Recherchez, filtrez puis ouvrez un épisode pour préparer votre session.</p></section>

	<section class="controls" aria-label="Recherche et filtres">
		<form onsubmit={(event) => { event.preventDefault(); submitSearch(); }}>
			<label class="sr-only" for="episode-search">Rechercher un épisode</label>
			<div><input bind:this={searchInput} id="episode-search" bind:value={searchValue} type="search" placeholder="Rechercher par titre" /><button type="submit">Rechercher</button></div>
		</form>
		<div class="filter-bar" role="group" aria-label="Filtrer par statut">
			{#each states as state}
				<button type="button" class:active={selectedState === state.value} aria-pressed={selectedState === state.value} onclick={() => updateQuery({ state: state.value, page: null })}>{state.label}</button>
			{/each}
		</div>
	</section>

	{#if errorMessage}
		<div class="message error" role="alert">{errorMessage}<button type="button" onclick={loadEpisodes}>Réessayer</button></div>
	{:else if isLoading}
		<div class="episode-grid" aria-label="Chargement des épisodes"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>
	{:else if episodes.length}
		<section class="episode-grid" aria-label="Liste des épisodes">
			{#each episodes as episode}
				<a class="episode-card {episode.state}" href={`/episodes/${episode.id}`}>
					<div class="card-topline"><span class="state {episode.state}"><i></i>{episodeStateLabel(episode.state)}</span><span aria-hidden="true">→</span></div>
					<div class="card-copy"><h2>{episode.title}</h2><p>{episode.is_active ? `${episode.time_slot} secondes par question` : 'Épisode désactivé'}</p></div>
					<dl><div><dt>Grille</dt><dd>{gridLabel(episode)}</dd></div><div><dt>État</dt><dd>{episodeStateLabel(episode.state)}</dd></div></dl>
				</a>
			{/each}
		</section>
	{:else}
		<section class="empty-state"><h2>Aucun épisode trouvé</h2><p>Modifiez votre recherche ou votre filtre pour élargir la liste.</p><button type="button" onclick={() => updateQuery({ state: null, search: null, page: null })}>Réinitialiser les filtres</button></section>
	{/if}

	{#if !isLoading && !errorMessage && count > 0}
		<nav class="pagination" aria-label="Pagination des épisodes">
			<button type="button" disabled={currentPage === 1} onclick={() => updateQuery({ page: String(currentPage - 1) })}>Précédent</button>
			<p>Page <strong>{currentPage}</strong> sur {totalPages} <span>· {count} épisodes</span></p>
			<button type="button" disabled={currentPage === totalPages} onclick={() => updateQuery({ page: String(currentPage + 1) })}>Suivant</button>
		</nav>
	{/if}

	{#if isCreateDialogOpen}
		<CreateEpisodeDialog onclose={() => isCreateDialogOpen = false} oncreated={handleEpisodeCreated} />
	{/if}
</main>

<style>
	:global(*) { box-sizing: border-box; }:global(html),:global(body) { min-width:320px; margin:0; background:#0f172a; color:#f8fafc; font-family:Inter,ui-sans-serif,system-ui,sans-serif; } main { width:min(100%,76rem); min-height:100dvh; margin:0 auto; padding:clamp(1.25rem,4vw,3rem); }.topbar,.topbar-actions,.controls,.filter-bar,.pagination { display:flex; align-items:center; gap:1rem; }.topbar { justify-content:space-between; }.brand { display:flex; align-items:center; gap:.7rem; color:#f8fafc; font-size:1.05rem; font-weight:750; text-decoration:none; }.brand img { width:2.5rem; height:2.5rem; border-radius:.75rem; background:#f8fafc; object-fit:cover; }.primary-action,.controls form button,.empty-state button { min-height:2.8rem; border:0; border-radius:.65rem; padding:.72rem 1rem; background:#7c3aed; color:white; cursor:pointer; font:inherit; font-size:.85rem; font-weight:750; }.primary-action:hover,.controls form button:hover,.empty-state button:hover { background:#8b5cf6; }.logout-button { min-height:2.8rem; border:0; padding:.72rem .35rem; background:transparent; color:#cbd5e1; cursor:pointer; font:inherit; font-size:.83rem; font-weight:700; }.logout-button:hover { color:#f8fafc; text-decoration:underline; }.intro { max-width:42rem; margin:clamp(3.5rem,9vw,7rem) 0 2.4rem; }.eyebrow { margin:0 0 .9rem; color:#c4b5fd; font-size:.72rem; font-weight:750; letter-spacing:.12em; text-transform:uppercase; } h1,h2,p { margin-top:0; } h1 { margin-bottom:1rem; font-size:clamp(2.5rem,6vw,4.6rem); line-height:.95; letter-spacing:-.07em; }.intro > p:last-child { margin-bottom:0; color:#cbd5e1; font-size:1.08rem; line-height:1.65; }.controls { justify-content:space-between; margin-bottom:1rem; border:1px solid #334155; border-radius:.8rem; padding:.8rem; background:#17213a; }.controls form { flex:1; }.controls label { display:block; margin-bottom:.42rem; color:#cbd5e1; font-size:.75rem; font-weight:700; }.controls form > div { display:flex; gap:.5rem; }.controls input { width:100%; min-height:2.65rem; border:1px solid #475569; border-radius:.55rem; padding:0 .75rem; background:#1e293b; color:#f8fafc; font:inherit; font-size:.86rem; }.controls input:focus { border-color:#a78bfa; outline:3px solid rgba(167,139,250,.22); }.controls form button { min-height:2.65rem; border-radius:.55rem; }.filter-bar { flex-wrap:wrap; justify-content:flex-end; }.filter-bar button { min-height:2.25rem; border:1px solid #475569; border-radius:999px; padding:.42rem .7rem; background:transparent; color:#cbd5e1; cursor:pointer; font:inherit; font-size:.76rem; font-weight:700; }.filter-bar button:hover { border-color:#64748b; color:#f8fafc; }.filter-bar button.active { border-color:#7c3aed; background:rgba(124,58,237,.2); color:#ddd6fe; }.episode-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; }.episode-card,.skeleton { min-height:18rem; border:1px solid #334155; border-radius:.95rem; background:#1e293b; }.episode-card { display:flex; flex-direction:column; padding:1.35rem; color:#f8fafc; text-decoration:none; transition:transform 180ms ease,border-color 180ms ease,background 180ms ease; }.episode-card:hover { transform:translateY(-3px); border-color:#64748b; background:#243247; }.episode-card.pending:hover { border-color:#38bdf8; }.episode-card.start:hover { border-color:#22c55e; }.episode-card.end:hover { border-color:#94a3b8; }.card-topline { display:flex; align-items:center; justify-content:space-between; color:#94a3b8; }.state { display:inline-flex; align-items:center; gap:.4rem; border-radius:999px; padding:.34rem .58rem; background:#334155; color:#cbd5e1; font-size:.72rem; font-weight:700; }.state i { width:.42rem; height:.42rem; border-radius:50%; background:currentColor; }.state.pending { background:rgba(56,189,248,.12); color:#7dd3fc; }.state.start { background:rgba(34,197,94,.12); color:#86efac; }.card-copy { margin-top:auto; }.card-copy h2 { margin-bottom:.8rem; font-size:1.35rem; letter-spacing:-.04em; }.card-copy p { margin-bottom:1.5rem; color:#cbd5e1; font-size:.88rem; } dl { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; margin:0; border-top:1px solid #475569; padding-top:1rem; } dt { margin-bottom:.3rem; color:#94a3b8; font-size:.68rem; } dd { margin:0; font-size:.78rem; font-weight:700; }.skeleton { border-color:#334155; background:linear-gradient(90deg,#1e293b 25%,#27354a 50%,#1e293b 75%); background-size:200% 100%; animation:shimmer 1.2s infinite; }.message,.empty-state { margin:0; border:1px solid #334155; border-radius:.8rem; padding:2rem; background:#17213a; text-align:center; }.message.error { display:flex; align-items:center; justify-content:space-between; border-color:rgba(239,68,68,.5); color:#fecaca; text-align:left; }.message button { border:0; background:transparent; color:#fecaca; cursor:pointer; font:inherit; font-weight:700; text-decoration:underline; }.empty-state h2 { margin-bottom:.6rem; }.empty-state p { color:#cbd5e1; }.pagination { justify-content:center; margin-top:1.5rem; }.pagination button { min-height:2.6rem; border:1px solid #475569; border-radius:.55rem; padding:.6rem .85rem; background:#1e293b; color:#f8fafc; cursor:pointer; font:inherit; font-size:.8rem; font-weight:700; }.pagination button:disabled { cursor:not-allowed; opacity:.45; }.pagination p { margin:0; color:#cbd5e1; font-size:.83rem; }.pagination strong { color:#f8fafc; }.pagination span { color:#94a3b8; }.primary-action:focus-visible,.logout-button:focus-visible,.controls input:focus-visible,.controls button:focus-visible,.filter-bar button:focus-visible,.episode-card:focus-visible,.pagination button:focus-visible,.message button:focus-visible,.empty-state button:focus-visible { outline:3px solid #a78bfa; outline-offset:3px; } @keyframes shimmer { to { background-position:-200% 0; } } @media (max-width:850px) { .controls { align-items:stretch; flex-direction:column; }.filter-bar { justify-content:flex-start; }.episode-grid { grid-template-columns:1fr 1fr; } } @media (max-width:520px) { main { padding:1.25rem 1rem 2rem; }.topbar { align-items:flex-start; flex-direction:column; }.topbar-actions { width:100%; justify-content:space-between; }.intro { margin-top:4rem; }.controls form > div { flex-direction:column; }.episode-grid { grid-template-columns:1fr; }.pagination { align-items:stretch; flex-wrap:wrap; }.pagination p { width:100%; order:-1; text-align:center; }.pagination button { flex:1; } } @media (prefers-reduced-motion:reduce) { *,*::before,*::after { animation-duration:.01ms !important; transition-duration:.01ms !important; } }
	.controls .sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; }
</style>
