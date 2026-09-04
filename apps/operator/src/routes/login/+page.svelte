<script lang="ts">
	import { goto } from '$app/navigation';
	import { saveToken } from '$lib/session';
	type LoginResponse = { token?: string; non_field_errors?: string[]; detail?: string };
	const api = (import.meta.env.PUBLIC_API_URL ?? '').replace(/\/$/, '');
	let username = $state('');
	let password = $state('');
	let submitting = $state(false);
	let errorMessage = $state('');
	async function login() {
		errorMessage = '';
		submitting = true;
		try {
			const response = await fetch(`${api}/api/auth/login/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
			const payload: LoginResponse = await response.json().catch(() => ({}));
			if (!response.ok || !payload.token) throw new Error(payload.non_field_errors?.[0] ?? payload.detail ?? 'Connexion impossible.');
			saveToken(payload.token);
			await goto('/');
		} catch (error) { errorMessage = error instanceof Error ? error.message : 'La connexion est indisponible.'; }
		finally { submitting = false; }
	}
</script>
<svelte:head><title>Connexion opérateur · La Grille</title></svelte:head>
<main><section><h1>Connexion opérateur</h1><p>Utilisez vos identifiants pour accéder à votre session.</p><form onsubmit={(event) => { event.preventDefault(); login(); }}><label for="username">Nom d’utilisateur</label><input id="username" autocomplete="username" bind:value={username} required /><label for="password">Mot de passe</label><input id="password" type="password" autocomplete="current-password" bind:value={password} required />{#if errorMessage}<p class="error" role="alert">{errorMessage}</p>{/if}<button type="submit" disabled={submitting}>{submitting ? 'Connexion…' : 'Se connecter'}</button></form></section></main>
<style>
	main { display: grid; min-height: 100dvh; place-items: center; padding: 1.5rem; background: #18181b; }
	section { width: min(100%, 27rem); border: 1px solid #3f3f46; border-radius: .5rem; padding: 2rem; background: #27272a; }
	h1 { margin: 0 0 .75rem; font-size: 1.5rem; }
	p { margin: 0; color: #d4d4d8; line-height: 1.5; }
	form { display: grid; gap: .6rem; margin-top: 1.75rem; }
	label { font-size: .875rem; font-weight: 650; }
	input, button { min-height: 2.65rem; border-radius: .4rem; font: inherit; }
	input { border: 1px solid #52525b; padding: 0 .7rem; background: #18181b; color: #fafafa; }
	button { margin-top: .6rem; border: 0; background: #a855f7; color: #fff; font-weight: 700; cursor: pointer; }
	button:disabled { opacity: .6; cursor: wait; }
	.error { color: #fca5a5; }
</style>
