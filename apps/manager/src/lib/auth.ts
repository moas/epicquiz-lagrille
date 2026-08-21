import { goto } from '$app/navigation';
import { createStore } from 'zustand/vanilla';

const TOKEN_KEY = 'lagrille-manager-token';

type SessionState = {
	token: string | null;
	hydrate: () => void;
	setToken: (token: string) => void;
	clearToken: () => void;
};

export const sessionStore = createStore<SessionState>()((set) => ({
	token: null,
	hydrate: () => set({ token: localStorage.getItem(TOKEN_KEY) }),
	setToken: (token) => {
		localStorage.setItem(TOKEN_KEY, token);
		set({ token });
	},
	clearToken: () => {
		localStorage.removeItem(TOKEN_KEY);
		set({ token: null });
	}
}));

export function hasManagerToken() {
	return Boolean(sessionStore.getState().token);
}

export function saveManagerToken(token: string) {
	sessionStore.getState().setToken(token);
}

export async function logout() {
	const { token } = sessionStore.getState();

	try {
		if (token) {
			await fetch('/api/auth/logout/', {
				method: 'POST',
				headers: { Authorization: `Token ${token}` }
			});
		}
	} finally {
		sessionStore.getState().clearToken();
		await goto('/login', { replaceState: true });
	}
}
