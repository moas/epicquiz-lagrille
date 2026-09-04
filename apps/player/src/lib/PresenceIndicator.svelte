<script lang="ts">
	import { onMount } from 'svelte';
	import { HEARTBEAT_PONG_EVENT, heartbeatEvents } from '$lib/heartbeat';
	let hasRecentPong = $state(false);
	let pongTimeout: ReturnType<typeof setTimeout> | null = null;
	onMount(() => {
		const markPongReceived = () => { hasRecentPong = true; if (pongTimeout) clearTimeout(pongTimeout); pongTimeout = setTimeout(() => { hasRecentPong = false; }, 60_000); };
		heartbeatEvents.addEventListener(HEARTBEAT_PONG_EVENT, markPongReceived);
		return () => { heartbeatEvents.removeEventListener(HEARTBEAT_PONG_EVENT, markPongReceived); if (pongTimeout) clearTimeout(pongTimeout); };
	});
</script>
<span class:connected={hasRecentPong} class="presence" role="status" aria-label={hasRecentPong ? 'Connexion temps réel active' : 'Connexion temps réel indisponible'}></span>
<style>.presence { position: fixed; top: 1rem; right: 1rem; z-index: 10; width: .75rem; height: .75rem; border: 2px solid #0f172a; border-radius: 50%; background: #ef4444; box-shadow: 0 0 0 1px rgba(248,250,252,.36); } .presence.connected { background: #22c55e; }</style>
