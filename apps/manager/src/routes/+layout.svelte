<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	import { hasManagerToken, sessionStore } from '$lib/auth';

	let { children } = $props();
	let isCheckingSession = $state(true);

	onMount(async () => {
		sessionStore.getState().hydrate();
		const isLoginPage = page.url.pathname === '/login';
		const hasToken = hasManagerToken();

		if (!hasToken && !isLoginPage) {
			await goto('/login', { replaceState: true });
			isCheckingSession = false;
			return;
		}

		if (hasToken && isLoginPage) {
			await goto('/', { replaceState: true });
			isCheckingSession = false;
			return;
		}

		isCheckingSession = false;
	});
</script>

<svelte:head>
	<link rel="icon" href="/brand-icon.png" />
	<meta name="theme-color" content="#0F172A" />
</svelte:head>

{#if isCheckingSession && page.url.pathname !== '/login'}
	<div class="session-check" role="status">Vérification de votre session…</div>
{:else}
	{@render children()}
{/if}

<style>
	.session-check {
		display: grid;
		min-height: 100dvh;
		place-items: center;
		background: #0f172a;
		color: #cbd5e1;
		font: 0.9rem Inter, ui-sans-serif, system-ui, sans-serif;
	}
</style>
