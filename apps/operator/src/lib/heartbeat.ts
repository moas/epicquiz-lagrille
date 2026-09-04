import { getToken, subscribe } from '$lib/session';

export const PONG_EVENT = 'heartbeat:pong';
export const heartbeatEvents = new EventTarget();
let socket: WebSocket | null = null;
let pingInterval: ReturnType<typeof setInterval> | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

function websocketUrl() {
	const base = import.meta.env.PUBLIC_WS_URL ?? import.meta.env.PUBLIC_API_URL ?? window.location.origin;
	const url = new URL(base, window.location.origin);
	url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
	url.pathname = '/ws/ping/';
	url.search = '';
	url.hash = '';
	return url.toString();
}
function disconnect() {
	if (pingInterval) clearInterval(pingInterval);
	if (reconnectTimeout) clearTimeout(reconnectTimeout);
	pingInterval = null;
	reconnectTimeout = null;
	const activeSocket = socket;
	socket = null;
	activeSocket?.close();
}
function connect(token: string) {
	disconnect();
	const activeSocket = new WebSocket(websocketUrl(), ['drf-token', token]);
	socket = activeSocket;
	activeSocket.onopen = () => {
		if (socket !== activeSocket) return;
		activeSocket.send('ping');
		pingInterval = setInterval(() => {
			if (socket === activeSocket && activeSocket.readyState === WebSocket.OPEN) activeSocket.send('ping');
		}, 10_000);
	};
	activeSocket.onmessage = (event) => {
		if (socket === activeSocket && event.data === 'pong') heartbeatEvents.dispatchEvent(new CustomEvent(PONG_EVENT));
	};
	activeSocket.onclose = () => {
		if (socket !== activeSocket) return;
		socket = null;
		if (pingInterval) clearInterval(pingInterval);
		pingInterval = null;
		reconnectTimeout = setTimeout(() => connect(token), 5_000);
	};
}
export function startHeartbeat() {
	const unsubscribe = subscribe((token) => { if (token) connect(token); else disconnect(); });
	const token = getToken();
	if (token) connect(token);
	return () => { unsubscribe(); disconnect(); };
}
