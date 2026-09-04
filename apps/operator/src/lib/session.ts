const TOKEN_KEY = 'lagrille-operator-token';
let token: string | null = null;
const subscribers = new Set<(value: string | null) => void>();
function publish() { subscribers.forEach((subscriber) => subscriber(token)); }
export function hydrate() { token = localStorage.getItem(TOKEN_KEY); publish(); }
export function hasToken() { return Boolean(token); }
export function getToken() { return token; }
export function saveToken(value: string) { token = value; localStorage.setItem(TOKEN_KEY, value); publish(); }
export function clearToken() { token = null; localStorage.removeItem(TOKEN_KEY); publish(); }
export function subscribe(subscriber: (value: string | null) => void) { subscribers.add(subscriber); return () => subscribers.delete(subscriber); }
