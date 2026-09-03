<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	import { hasManagerToken, sessionStore } from '$lib/auth';
	import { startHeartbeat } from '$lib/heartbeat';
	import PresenceIndicator from '$lib/PresenceIndicator.svelte';

	let { children } = $props();
	let isCheckingSession = $state(true);

	onMount(() => {
		sessionStore.getState().hydrate();
		const stopHeartbeat = startHeartbeat();

		void (async () => {
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
		})();

		return stopHeartbeat;
	});
</script>

<svelte:head>
	<link rel="icon" href="/brand-icon.png" />
	<meta name="theme-color" content="#0F172A" />
</svelte:head>

{#if isCheckingSession && page.url.pathname !== '/login'}
	<div class="session-check" role="status">Vérification de votre session…</div>
{:else}
	{#if page.url.pathname !== '/login'}
		<PresenceIndicator />
	{/if}
	{@render children()}
{/if}

<style>
	:global(input::placeholder),
	:global(textarea::placeholder) {
		color: #94a3b8;
		opacity: 1;
		font-family: Inter, ui-sans-serif, system-ui, sans-serif;
		font-size: 0.875rem;
		font-weight: 500;
		letter-spacing: 0;
	}

	.session-check {
		display: grid;
		min-height: 100dvh;
		place-items: center;
		background: #0f172a;
		color: #cbd5e1;
		font: 0.9rem Inter, ui-sans-serif, system-ui, sans-serif;
	}
</style>
