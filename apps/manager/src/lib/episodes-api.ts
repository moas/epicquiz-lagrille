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

export type Answer = { id: string; answer: string; is_correct: boolean };
export type Question = {
	id: string;
	question: string;
	level: number;
	tags: string[];
	reason: string | null;
	answers: Answer[];
	is_active: boolean;
};
export type UpdateQuestionPayload = Partial<Pick<Question, 'question' | 'level' | 'tags' | 'reason' | 'is_active'>>;
export type CreateQuestionPayload = {
	question: string;
	level: number;
	tags?: string[];
	reason?: string;
	answers: Array<Pick<Answer, 'answer' | 'is_correct'>>;
};
export type QueryConfig = { id: string; join: 'and' | 'or'; mode: 'select' | 'unselect'; tags: string[] | null; level: number[] | null };
export type SpecialAttribute = {
	id: string;
	is_active: boolean;
	type: 'steal' | 'prize';
	name?: string;
	description?: string | null;
};
export type GridCell = { id: string; name: string; x: number; y: number; challenge_id: string | null };
export type PreparedGrid = {
	id: string;
	rows: number;
	columns: number;
	empty_cell_count: number;
	point_distribution: Record<string, number>;
	state: 'configured' | 'positions_drawn' | 'attributes_drawn';
	cells: GridCell[];
};
export type EpisodeQuestion = Question & { is_selected: boolean };
export type PaginatedEpisodeQuestions = {
	count: number;
	next: string | null;
	previous: string | null;
	results: EpisodeQuestion[];
	eligible_count: number;
	selected_count: number;
	selected_by_level: Record<string, number>;
};

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

export function getQuestion(id: string) {
	return request<Question>(`/api/qa/questions/${id}/`, {}, 'Impossible de charger cette question.');
}

export function createQuestion(payload: CreateQuestionPayload) {
	return request<Question>('/api/qa/questions/', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	}, 'Impossible de créer cette question.');
}

export function updateQuestion(id: string, payload: UpdateQuestionPayload) {
	return request<Question>(`/api/qa/questions/${id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	}, 'Impossible d’enregistrer cette question.');
}

export async function deleteQuestion(id: string) {
	await request<void>(`/api/qa/questions/${id}/`, { method: 'DELETE' }, 'Impossible de supprimer cette question.');
}

export function createQuestionProposition(questionId: string, payload: Pick<Answer, 'answer' | 'is_correct'>) {
	return request<Answer>(`/api/qa/questions/${questionId}/propositions/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	}, 'Impossible d’ajouter cette proposition.');
}
export function getQueryConfigs(episodeId: string) { return request<QueryConfig[]>(`/api/episodes/${episodeId}/query-configs/`, {}, 'Impossible de charger les règles.'); }
export function createQueryConfig(episodeId: string, payload: Omit<QueryConfig, 'id'>) { return request<QueryConfig>(`/api/episodes/${episodeId}/query-configs/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }, 'Impossible d’ajouter cette règle.'); }
export async function deleteQueryConfig(episodeId: string, id: string) { await request<void>(`/api/episodes/${episodeId}/query-configs/${id}/`, { method: 'DELETE' }, 'Impossible de supprimer cette règle.'); }
export function getEpisodeQuestions(episodeId: string, parameters = new URLSearchParams()) { const query = parameters.size ? `?${parameters.toString()}` : ''; return request<PaginatedEpisodeQuestions>(`/api/episodes/${episodeId}/questions/${query}`, {}, 'Impossible de charger les questions de cet épisode.'); }
export function selectEpisodeQuestion(episodeId: string, questionId: string) { return request<{ question_id: string }>(`/api/episodes/${episodeId}/questions/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question_id: questionId }) }, 'Impossible de sélectionner cette question.'); }
export async function unselectEpisodeQuestion(episodeId: string, questionId: string) { await request<void>(`/api/episodes/${episodeId}/questions/${questionId}/`, { method: 'DELETE' }, 'Impossible de retirer cette question.'); }
export function getSelectedEpisodeQuestions(episodeId: string) { return request<Question[]>(`/api/episodes/${episodeId}/selected-questions/`, {}, 'Impossible de charger les questions retenues.'); }
export function getPreparedGrid(episodeId: string) { return request<PreparedGrid>(`/api/episodes/${episodeId}/grid/`, {}, 'Impossible de charger la grille préparée.'); }
export function saveChallengeDispatch(episodeId: string, assignments: Array<{ position: number; question_id: string }>) { return request<PreparedGrid>(`/api/episodes/${episodeId}/challenge-dispatch/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ assignments }) }, 'Impossible d’enregistrer la répartition des challenges.'); }
export function saveAttributeDispatch(episodeId: string, assignments: Array<{ cell_id: string; attribute_id: string }>) { return request<PreparedGrid>(`/api/episodes/${episodeId}/attribute-dispatch/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ assignments }) }, 'Impossible d’enregistrer la répartition des attributs.'); }
export function getStealAttributes(episodeId: string) { return request<Array<Omit<SpecialAttribute, 'type'>>>(`/api/episodes/${episodeId}/steal-attributes/`, {}, 'Impossible de charger les attributs spéciaux.').then((items) => items.map((item) => ({ ...item, type: 'steal' as const }))); }
export function getPrizeAttributes(episodeId: string) { return request<Array<Omit<SpecialAttribute, 'type'>>>(`/api/episodes/${episodeId}/prize-attributes/`, {}, 'Impossible de charger les attributs spéciaux.').then((items) => items.map((item) => ({ ...item, type: 'prize' as const }))); }
export function createStealAttribute(episodeId: string) { return request<Omit<SpecialAttribute, 'type'>>(`/api/episodes/${episodeId}/steal-attributes/`, { method: 'POST' }, 'Impossible d’ajouter cet attribut.').then((item) => ({ ...item, type: 'steal' as const })); }
export function createPrizeAttribute(episodeId: string, payload: Pick<SpecialAttribute, 'name' | 'description'>) { return request<Omit<SpecialAttribute, 'type'>>(`/api/episodes/${episodeId}/prize-attributes/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }, 'Impossible d’ajouter ce lot.').then((item) => ({ ...item, type: 'prize' as const })); }
export async function deleteSpecialAttribute(episodeId: string, attribute: SpecialAttribute) { const collection = attribute.type === 'steal' ? 'steal-attributes' : 'prize-attributes'; await request<void>(`/api/episodes/${episodeId}/${collection}/${attribute.id}/`, { method: 'DELETE' }, 'Impossible de supprimer cet attribut.'); }

export function episodeStateLabel(state: EpisodeState) {
	return { pending: 'À préparer', start: 'En cours', end: 'Terminé' }[state];
}

export function gridLabel(episode: Episode) {
	const grid = episode.metadata.grid_config;
	return grid ? `${grid.rows} × ${grid.columns} cases` : 'À configurer';
}
