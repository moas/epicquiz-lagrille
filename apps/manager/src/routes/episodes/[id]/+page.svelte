<script lang="ts">
	import { onMount } from 'svelte';
	import { getEpisode, episodeStateLabel, gridLabel, type Episode } from '$lib/episodes-api';
	import { logout } from '$lib/auth';
	import type { PageProps } from './$types';

	let { params }: PageProps = $props();
	let episode = $state<Episode | null>(null);
	let errorMessage = $state('');
	let isLoading = $state(true);

	onMount(async () => {
		try {
			episode = await getEpisode(params.id);
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Impossible de charger cet épisode.';
		} finally {
			isLoading = false;
		}
	});

</script>

<svelte:head><title>{episode ? `${episode.title} · EpicQuiz - La Grille` : 'Épisode · EpicQuiz - La Grille'}</title></svelte:head>

<main id="content">
	<div class="page-actions"><a href="/">← Tous les épisodes</a><button type="button" onclick={logout}>Déconnexion</button></div>
	{#if isLoading}
		<p class="loading" role="status">Chargement de l’espace de gestion…</p>
	{:else if errorMessage}
		<section class="message" role="alert"><h1>Impossible d’ouvrir l’épisode</h1><p>{errorMessage}</p><a href="/">Retour aux épisodes</a></section>
	{:else if episode}
		<div class="workspace">
			<section class="board" aria-labelledby="episode-title">
				<header class="board-header"><div><p class="eyebrow">Épisode en préparation</p><h1 id="episode-title">{episode.title}</h1><p>{episode.time_slot} secondes par question · {gridLabel(episode)}</p></div><span class="state {episode.state}"><i></i>{episodeStateLabel(episode.state)}</span></header>

				<section class="ready-panel" aria-labelledby="ready-title"><div><p class="eyebrow">Prochaine étape</p><h2 id="ready-title">Composez votre session</h2><p>Ajoutez les questions, construisez la grille puis invitez les personnes qui participeront à l’émission.</p></div><span>{gridLabel(episode)}</span></section>

				<section class="manager-grid" aria-label="Étapes de préparation">
					<a id="questions" class="manager-card" href={`/episodes/${episode.id}/questions`}><span class="card-number">01</span><strong>Questions</strong><p>Composer et valider le questionnaire de cette session.</p><b>Gérer les questions <span aria-hidden="true">→</span></b></a>
					<a id="grid" class="manager-card featured" href={`/episodes/${episode.id}/grid`}><span class="card-number">02</span><strong>Grille</strong><p>Préparer les cases, les points et les attributs spéciaux.</p><b>Configurer la grille <span aria-hidden="true">→</span></b></a>
					<a id="participants" class="manager-card" href={`/episodes/${episode.id}/participants`}><span class="card-number">03</span><strong>Participants</strong><p>Inviter les joueurs, l’écran et les opérateurs.</p><b>Gérer les participants <span aria-hidden="true">→</span></b></a>
				</section>
			</section>

			<aside class="side-panel" aria-label="Menu de l’épisode">
				<div class="episode-summary"><p class="eyebrow">Session</p><h2>{episode.title}</h2><span class="state {episode.state}"><i></i>{episodeStateLabel(episode.state)}</span></div>
				<nav aria-label="Navigation de préparation"><a class="active" href="#content"><span>Vue d’ensemble</span><b>⌂</b></a><a href={`/episodes/${episode.id}/questions`}><span>Questions</span><b>01</b></a><a href={`/episodes/${episode.id}/grid`}><span>Grille</span><b>02</b></a><a href={`/episodes/${episode.id}/participants`}><span>Participants</span><b>03</b></a></nav>
				<div class="side-details"><p>Durée par question</p><strong>{episode.time_slot} secondes</strong><p>Configuration</p><strong>{gridLabel(episode)}</strong></div>
				<a class="back-link" href="/">← Retour aux épisodes</a>
			</aside>
		</div>
	{/if}
</main>

<style>
	:global(*) { box-sizing:border-box; }:global(html),:global(body) { min-width:320px; margin:0; background:#0f172a; color:#f8fafc; font-family:Inter,ui-sans-serif,system-ui,sans-serif; } main { width:min(100%,82rem); min-height:100dvh; margin:0 auto; padding:clamp(1.25rem,4vw,3rem); }.page-actions { display:flex; align-items:center; justify-content:space-between; gap:1rem; }.page-actions a,.page-actions button { min-height:2.75rem; border:0; padding:.5rem; background:transparent; color:#c4b5fd; cursor:pointer; font:inherit; font-size:.88rem; font-weight:700; text-decoration:none; }.page-actions button { color:#cbd5e1; }.page-actions a:hover,.page-actions button:hover { color:#f8fafc; text-decoration:underline; }.loading { margin-top:7rem; color:#cbd5e1; text-align:center; }.message { max-width:34rem; margin:7rem auto; border:1px solid rgba(239,68,68,.5); border-radius:.8rem; padding:2rem; background:#17213a; }.message p { color:#fecaca; line-height:1.6; }.message a { color:#c4b5fd; font-weight:700; }.workspace { display:grid; grid-template-columns:minmax(0,1fr) 18rem; gap:1.5rem; align-items:start; margin-top:clamp(2rem,6vw,5rem); }.board { min-width:0; }.board-header { display:flex; align-items:flex-start; justify-content:space-between; gap:1.5rem; margin-bottom:2rem; }.eyebrow { margin:0 0 .7rem; color:#c4b5fd; font-size:.7rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; } h1,h2,p { margin-top:0; } h1 { margin-bottom:.75rem; color:#f8fafc; font-size:clamp(2.4rem,5vw,4.4rem); line-height:.95; letter-spacing:-.07em; }.board-header > div > p:last-child { margin-bottom:0; color:#cbd5e1; }.state { display:inline-flex; align-items:center; gap:.4rem; border-radius:999px; padding:.4rem .65rem; background:#334155; color:#cbd5e1; font-size:.73rem; font-weight:750; white-space:nowrap; }.state i { width:.45rem; height:.45rem; border-radius:50%; background:currentColor; }.state.pending { background:rgba(56,189,248,.12); color:#7dd3fc; }.state.start { background:rgba(34,197,94,.12); color:#86efac; }.ready-panel { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin-bottom:1rem; border:1px solid rgba(124,58,237,.55); border-radius:1rem; padding:1.4rem; background:linear-gradient(135deg,rgba(124,58,237,.2),rgba(30,41,59,.85)); }.ready-panel .eyebrow { margin-bottom:.5rem; }.ready-panel h2 { margin-bottom:.5rem; color:#f8fafc; font-size:1.25rem; letter-spacing:-.035em; }.ready-panel p:last-child { max-width:35rem; margin:0; color:#cbd5e1; font-size:.86rem; line-height:1.55; }.ready-panel > span { flex:none; border-radius:.55rem; padding:.55rem .65rem; background:rgba(15,23,42,.5); color:#ddd6fe; font-size:.76rem; font-weight:750; }.manager-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; }.manager-card { display:flex; min-height:16rem; flex-direction:column; align-items:flex-start; border:1px solid #334155; border-radius:.9rem; padding:1.25rem; background:#1e293b; color:#f8fafc; cursor:pointer; font:inherit; text-align:left; text-decoration:none; transition:transform 180ms ease,border-color 180ms ease,background 180ms ease; }.manager-card:hover { transform:translateY(-3px); border-color:#a78bfa; background:#243247; }.manager-card.featured { border-color:rgba(124,58,237,.65); }.card-number { margin-bottom:auto; color:#a78bfa; font-size:.73rem; font-weight:800; letter-spacing:.1em; }.manager-card strong { font-size:1.05rem; }.manager-card p { margin:.65rem 0 1rem; color:#cbd5e1; font-size:.84rem; line-height:1.55; }.manager-card b { color:#c4b5fd; font-size:.78rem; }.manager-card b span { margin-left:.2rem; }.side-panel { position:sticky; top:1.25rem; overflow:hidden; border:1px solid #334155; border-radius:1rem; background:#1e293b; }.episode-summary { padding:1.25rem; border-bottom:1px solid #334155; }.episode-summary .eyebrow { margin-bottom:.5rem; }.episode-summary h2 { overflow:hidden; margin:0 0 .9rem; color:#f8fafc; font-size:1rem; line-height:1.35; text-overflow:ellipsis; white-space:nowrap; }.side-panel nav { padding:.7rem; }.side-panel nav a,.side-panel nav button { display:flex; width:100%; align-items:center; justify-content:space-between; min-height:2.75rem; border:0; border-radius:.55rem; padding:0 .65rem; background:transparent; color:#cbd5e1; cursor:pointer; font:inherit; font-size:.83rem; font-weight:700; text-align:left; text-decoration:none; }.side-panel nav a:hover,.side-panel nav button:hover { background:#334155; color:#f8fafc; }.side-panel nav a.active { background:rgba(124,58,237,.18); color:#ddd6fe; }.side-panel nav b { color:#94a3b8; font-size:.68rem; }.side-details { margin:0 .7rem; border-top:1px solid #334155; padding:1rem .55rem; }.side-details p { margin:0 0 .25rem; color:#94a3b8; font-size:.69rem; }.side-details strong { display:block; margin-bottom:.85rem; color:#f8fafc; font-size:.78rem; }.side-details strong:last-child { margin-bottom:0; }.back-link { display:block; border-top:1px solid #334155; padding:1rem 1.25rem; color:#c4b5fd; font-size:.78rem; font-weight:750; text-decoration:none; }.back-link:hover { color:#f8fafc; }.page-actions a:focus-visible,.page-actions button:focus-visible,.manager-card:focus-visible,.side-panel a:focus-visible,.side-panel button:focus-visible { outline:3px solid #a78bfa; outline-offset:3px; } @media (max-width:1000px) { .workspace { grid-template-columns:1fr; }.side-panel { position:static; display:grid; grid-template-columns:1.1fr 1fr; }.episode-summary { border-bottom:0; border-right:1px solid #334155; }.side-panel nav { border-left:1px solid #334155; }.side-details,.back-link { grid-column:1 / -1; } }.side-panel nav { grid-row:span 2; } @media (max-width:720px) { .board-header,.ready-panel { align-items:flex-start; flex-direction:column; }.manager-grid { grid-template-columns:1fr; }.manager-card { min-height:12.5rem; }.side-panel { display:block; }.episode-summary { border-right:0; border-bottom:1px solid #334155; }.side-panel nav { border-left:0; }.side-panel nav { grid-row:auto; } } @media (prefers-reduced-motion:reduce) { *,*::before,*::after { transition-duration:.01ms !important; } }
</style>
