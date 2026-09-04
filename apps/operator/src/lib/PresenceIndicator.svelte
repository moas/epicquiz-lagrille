<script lang="ts">
	import { onMount } from 'svelte';
	import { PONG_EVENT, heartbeatEvents } from '$lib/heartbeat';
	let connected = $state(false);
	let timeout: ReturnType<typeof setTimeout> | null = null;
	onMount(() => {
		const pong = () => { connected = true; if (timeout) clearTimeout(timeout); timeout = setTimeout(() => { connected = false; }, 60_000); };
		heartbeatEvents.addEventListener(PONG_EVENT, pong);
		return () => { heartbeatEvents.removeEventListener(PONG_EVENT, pong); if (timeout) clearTimeout(timeout); };
	});
</script>
<span class:connected class="presence" role="status" aria-label={connected ? 'Connexion temps réel active' : 'Connexion temps réel indisponible'}></span>
<style>.presence{position:fixed;top:1rem;right:1rem;z-index:10;width:.75rem;height:.75rem;border:2px solid #18181b;border-radius:50%;background:#ef4444;box-shadow:0 0 0 1px rgba(250,250,250,.36)}.presence.connected{background:#22c55e}</style>
