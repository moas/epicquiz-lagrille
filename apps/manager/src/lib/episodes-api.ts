import { sessionStore } from '$lib/auth';

const apiBaseUrl = (import.meta.env.PUBLIC_API_URL ?? '').replace(/\/$/, '');

export type EpisodeState = 'pending' | 'start' | 'end';

export type Episode = {
	id: string;
	title: string;
	time_slot: number;
	metadata: {
		grid_config?: GridConfig;
	};
	is_active: boolean;
	state: EpisodeState;
};

export type GridConfig = {
	version: number;
	rows: number;
	columns: number;
	empty_cell_count: number;
	point_distribution: Record<string, number>;
	coordinate_format: { x: string; y: string };
};

export type ParticipantRole = 'PLAYER' | 'SCREEN' | 'PRESENTER' | 'OPERATOR';

export type Participant = {
	id: string;
	username: string;
	name: string;
	role: ParticipantRole;
	is_active: boolean;
	tags: string[] | null;
};

export type Question = { id: string; question: string; level: number; tags: string[]; is_active: boolean };
export type QueryConfig = { id: string; join: 'and' | 'or'; mode: 'select' | 'unselect'; tags: string[] | null; level: number[] | null };

export type PaginatedEpisodes = {
	count: number;
	next: string | null;
	previous: string | null;
	results: Episode[];
};

export type CreateEpisodePayload = {
	title: string;
	time_slot: number;
	is_active: boolean;
};

export type UpdateEpisodePayload = Partial<Pick<Episode, 'title' | 'time_slot' | 'is_active' | 'metadata'>>;

export class ApiError extends Error {
	fieldErrors: Record<string, string>;

	constructor(message: string, fieldErrors: Record<string, string> = {}) {
		super(message);
		this.fieldErrors = fieldErrors;
	}
}

function extractFieldErrors(payload: unknown) {
	if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return {};

	return Object.fromEntries(
		Object.entries(payload).map(([field, value]) => [
			field,
			Array.isArray(value) ? value.join(' ') : String(value)
		])
	);
}

async function request<T>(path: string, options: RequestInit = {}, fallbackMessage = 'Impossible de charger les épisodes.') {
	const token = sessionStore.getState().token;
	const response = await fetch(`${apiBaseUrl}${path}`, {
		...options,
		headers: {
			...(token ? { Authorization: `Token ${token}` } : {}),
			...options.headers
		}
	});

	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		throw new ApiError(
			response.status === 401 ? 'Votre session a expiré.' : fallbackMessage,
			extractFieldErrors(payload)
		);
	}

	if (response.status === 204) return undefined as T;

	return (await response.json()) as T;
}

export function getEpisodes(parameters: URLSearchParams) {
	return request<PaginatedEpisodes>(`/api/episodes/?${parameters.toString()}`);
}

export function getEpisode(id: string) {
	return request<Episode>(`/api/episodes/${id}/`);
}

export function createEpisode(payload: CreateEpisodePayload) {
	return request<Episode>('/api/episodes/', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	}, 'Impossible d’enregistrer cet épisode.');
}

export function updateEpisode(id: string, payload: UpdateEpisodePayload) {
	return request<Episode>(`/api/episodes/${id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	}, 'Impossible d’enregistrer la configuration de la grille.');
}

export function getParticipants(episodeId: string, parameters = new URLSearchParams()) {
	const query = parameters.size ? `?${parameters.toString()}` : '';
	return request<Participant[]>(`/api/episodes/${episodeId}/participants/${query}`, {}, 'Impossible de charger les participants.');
}

export function createParticipant(episodeId: string, payload: Pick<Participant, 'name' | 'role'>) {
	return request<Participant>(`/api/episodes/${episodeId}/participants/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	}, 'Impossible d’ajouter ce participant.');
}

export async function deactivateParticipant(episodeId: string, participantId: string) {
	await request<void>(`/api/episodes/${episodeId}/participants/${participantId}/`, {
		method: 'DELETE'
	}, 'Impossible de désactiver ce participant.');
}

export function updateParticipant(episodeId: string, participantId: string, payload: Partial<Pick<Participant, 'is_active'>>) {
	return request<Participant>(`/api/episodes/${episodeId}/participants/${participantId}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	}, 'Impossible de mettre à jour ce participant.');
}

export async function getQuestions() {
	const response = await request<Question[] | PaginatedQuestions>('/api/qa/questions/', {}, 'Impossible de charger les questions.');
	return Array.isArray(response) ? response : response.results;
}

export type QuestionImportResult = { imported_questions: number; reused_propositions: number; skipped_questions: string[] };

export function importQuestions(file: File) {
	const formData = new FormData();
	formData.append('file', file);
	return request<QuestionImportResult>('/api/qa/questions/import/', { method: 'POST', body: formData }, 'Impossible d’importer ce fichier.');
}

type PaginatedQuestions = { count: number; next: string | null; previous: string | null; results: Question[] };

export function getQuestionPage(parameters: URLSearchParams) {
	return request<PaginatedQuestions>(`/api/qa/questions/?${parameters.toString()}`, {}, 'Impossible de charger les questions.');
}
export function getQueryConfigs(episodeId: string) { return request<QueryConfig[]>(`/api/episodes/${episodeId}/query-configs/`, {}, 'Impossible de charger les règles.'); }
export function createQueryConfig(episodeId: string, payload: Omit<QueryConfig, 'id'>) { return request<QueryConfig>(`/api/episodes/${episodeId}/query-configs/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }, 'Impossible d’ajouter cette règle.'); }
export async function deleteQueryConfig(episodeId: string, id: string) { await request<void>(`/api/episodes/${episodeId}/query-configs/${id}/`, { method: 'DELETE' }, 'Impossible de supprimer cette règle.'); }

export function episodeStateLabel(state: EpisodeState) {
	return { pending: 'À préparer', start: 'En cours', end: 'Terminé' }[state];
}

export function gridLabel(episode: Episode) {
	const grid = episode.metadata.grid_config;
	return grid ? `${grid.rows} × ${grid.columns} cases` : 'À configurer';
}
