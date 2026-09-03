<script lang="ts">
	import { onMount } from 'svelte';

	import { HEARTBEAT_PONG_EVENT, heartbeatEvents } from '$lib/heartbeat';

	const PONG_TIMEOUT_MS = 60_000;

	let hasRecentPong = $state(false);
	let pongTimeout: ReturnType<typeof setTimeout> | null = null;

	onMount(() => {
		function markPongReceived() {
			hasRecentPong = true;
			if (pongTimeout) clearTimeout(pongTimeout);
			pongTimeout = setTimeout(() => {
				hasRecentPong = false;
			}, PONG_TIMEOUT_MS);
		}

		heartbeatEvents.addEventListener(HEARTBEAT_PONG_EVENT, markPongReceived);

		return () => {
			heartbeatEvents.removeEventListener(HEARTBEAT_PONG_EVENT, markPongReceived);
			if (pongTimeout) clearTimeout(pongTimeout);
		};
	});
</script>

<span
	class:connected={hasRecentPong}
	class="presence-indicator"
	role="status"
	aria-label={hasRecentPong ? 'Connexion temps réel active' : 'Connexion temps réel indisponible'}
></span>

<style>
	.presence-indicator {
		position: fixed;
		top: 1rem;
		right: 1rem;
		z-index: 10;
		width: 0.75rem;
		height: 0.75rem;
		border: 2px solid #0f172a;
		border-radius: 50%;
		background: #ef4444;
		box-shadow: 0 0 0 1px rgba(248, 250, 252, 0.36);
	}

	.presence-indicator.connected {
		background: #22c55e;
	}
</style>
