<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { hasToken, hydrate } from '$lib/session';
	import { startHeartbeat } from '$lib/heartbeat';
	import PresenceIndicator from '$lib/PresenceIndicator.svelte';
	let { children } = $props();
	let checking = $state(true);
	onMount(() => {
		hydrate();
		const stop = startHeartbeat();
		void (async () => {
			const loginPage = page.url.pathname === '/login';
			if (!hasToken() && !loginPage) await goto('/login', { replaceState: true });
			else if (hasToken() && loginPage) await goto('/', { replaceState: true });
			checking = false;
		})();
		return stop;
	});
</script>
{#if checking && page.url.pathname !== '/login'}<div class="checking">Vérification de la session…</div>{:else}{#if page.url.pathname !== '/login'}<PresenceIndicator />{/if}{@render children()}{/if}
<style>:global(*){box-sizing:border-box}:global(body){margin:0;min-width:320px;background:#18181b;color:#fafafa;font-family:ui-sans-serif,system-ui,sans-serif}.checking{display:grid;min-height:100dvh;place-items:center;color:#a1a1aa}</style>
