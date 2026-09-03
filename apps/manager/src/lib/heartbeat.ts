import { sessionStore } from '$lib/auth';

export const HEARTBEAT_PONG_EVENT = 'heartbeat:pong';
export const heartbeatEvents = new EventTarget();

const PING_INTERVAL_MS = 15_000;
const RECONNECT_DELAY_MS = 5_000;

let socket: WebSocket | null = null;
let pingInterval: ReturnType<typeof setInterval> | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let currentToken: string | null = null;

function websocketUrl() {
	const baseUrl = import.meta.env.PUBLIC_WS_URL ?? import.meta.env.PUBLIC_API_URL ?? window.location.origin;
	const url = new URL(baseUrl, window.location.origin);
	url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
	url.pathname = '/ws/ping/';
	url.search = '';
	url.hash = '';
	return url.toString();
}

function clearTimers() {
	if (pingInterval) clearInterval(pingInterval);
	if (reconnectTimeout) clearTimeout(reconnectTimeout);
	pingInterval = null;
	reconnectTimeout = null;
}

function disconnect() {
	clearTimers();
	const activeSocket = socket;
	socket = null;
	activeSocket?.close();
}

function sendPing(activeSocket: WebSocket) {
	if (socket !== activeSocket || activeSocket.readyState !== WebSocket.OPEN) return;

	activeSocket.send('ping');
}

function connect(token: string) {
	disconnect();

	const activeSocket = new WebSocket(websocketUrl(), ['drf-token', token]);
	socket = activeSocket;

	activeSocket.onopen = () => {
		if (socket !== activeSocket) return;

		sendPing(activeSocket);
		pingInterval = setInterval(() => sendPing(activeSocket), PING_INTERVAL_MS);
	};

	activeSocket.onmessage = (event) => {
		if (socket !== activeSocket || event.data !== 'pong') return;

		heartbeatEvents.dispatchEvent(
			new CustomEvent(HEARTBEAT_PONG_EVENT, { detail: { receivedAt: Date.now() } })
		);
	};

	activeSocket.onclose = () => {
		if (socket !== activeSocket) return;

		socket = null;
		if (pingInterval) clearInterval(pingInterval);
		pingInterval = null;
		reconnectTimeout = setTimeout(() => connect(token), RECONNECT_DELAY_MS);
	};
}

export function startHeartbeat() {
	const unsubscribe = sessionStore.subscribe((state) => {
		if (state.token === currentToken) return;

		currentToken = state.token;
		if (currentToken) connect(currentToken);
		else disconnect();
	});

	currentToken = sessionStore.getState().token;
	if (currentToken) connect(currentToken);

	return () => {
		unsubscribe();
		currentToken = null;
		disconnect();
	};
}
