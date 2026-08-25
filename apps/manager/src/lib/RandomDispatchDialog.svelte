<script lang="ts">
	import { onMount } from 'svelte';
	import {
		assetUrl,
		saveAttributeDispatch,
		saveChallengeDispatch,
		type GridConfig,
		type GridCell,
		type PreparedGrid,
		type Question,
		type SpecialAttribute
	} from '$lib/episodes-api';

	type ChallengeAssignment = { position: number; question_id: string };
	type AttributeAssignment = { cell_id: string; attribute_id: string };
	type DispatchMode = 'challenges' | 'attributes';
	let { episodeId, config, mode, questions = [], attributes = [], cells = [], onclose, onsaved }: {
		episodeId: string;
		config: GridConfig;
		mode: DispatchMode;
		questions?: Question[];
		attributes?: SpecialAttribute[];
		cells?: GridCell[];
		onclose: () => void;
		onsaved: (grid: PreparedGrid) => void;
	} = $props();
	let challengeAssignments = $state<ChallengeAssignment[]>([]);
	let attributeAssignments = $state<AttributeAssignment[]>([]);
	let isConfirming = $state(false);
	let isSaving = $state(false);
	let errorMessage = $state('');
	let drawNumber = $state(0);

	const isChallenge = $derived(mode === 'challenges');
	const shuffledAttributes = $derived(attributeAssignments.map((assignment) => ({ assignment, attribute: attributes.find((attribute) => attribute.id === assignment.attribute_id)!, cell: cells.find((cell) => cell.id === assignment.cell_id)! })));
	const activeAttributes = $derived(attributes.filter((attribute) => attribute.is_active));

	function shuffle<T>(items: T[]) {
		const result = [...items];
		for (let index = result.length - 1; index > 0; index -= 1) {
			const otherIndex = Math.floor(Math.random() * (index + 1));
			[result[index], result[otherIndex]] = [result[otherIndex], result[index]];
		}
		return result;
	}

	function coordinateFor(position: number) {
		const x = config.coordinate_format.x.split(',').map((label) => label.trim());
		const y = config.coordinate_format.y.split(',').map((label) => label.trim());
		return `${x[Math.floor(position / config.columns)]}${y[position % config.columns]}`;
	}

	function questionsForChallengeDraw() {
		return Array.from({ length: 5 }, (_, index) => {
			const level = index + 1;
			const required = Number(config.point_distribution[String(level)] ?? 0);
			return shuffle(questions.filter((question) => question.level === level)).slice(0, required);
		}).flat();
	}

	function randomize() {
		errorMessage = ''; isConfirming = false; drawNumber += 1;
		if (mode === 'challenges') {
			const drawnQuestions = shuffle(questionsForChallengeDraw());
			const positions = shuffle(Array.from({ length: config.rows * config.columns }, (_, index) => index)).slice(0, drawnQuestions.length);
			challengeAssignments = drawnQuestions.map((question, index) => ({ position: positions[index], question_id: question.id }));
			return;
		}
		const candidates = shuffle(cells.filter((cell) => cell.challenge_id));
		attributeAssignments = shuffle(activeAttributes).map((attribute, index) => ({ cell_id: candidates[index]?.id ?? '', attribute_id: attribute.id })).filter((assignment) => assignment.cell_id);
	}

	onMount(randomize);

	async function save() {
		isSaving = true; errorMessage = '';
		try {
			const grid = mode === 'challenges'
				? await saveChallengeDispatch(episodeId, challengeAssignments)
				: await saveAttributeDispatch(episodeId, attributeAssignments);
			onsaved(grid); onclose();
		} catch (error) { errorMessage = error instanceof Error ? error.message : 'Impossible d’enregistrer cette répartition.'; }
		finally { isSaving = false; }
	}
</script>

<div class="backdrop" role="presentation" onclick={(event) => event.currentTarget === event.target && !isSaving && onclose()}>
	<dialog class="dialog" open aria-labelledby="dispatch-title">
		<header><div><p class="eyebrow">Tirage aléatoire · essai {drawNumber}</p><h2 id="dispatch-title">{isChallenge ? 'Répartir les challenges' : 'Attribuer les attributs'}</h2></div><button class="close" type="button" aria-label="Fermer" disabled={isSaving} onclick={onclose}>×</button></header>
		<p class="intro">{isChallenge ? 'Cette proposition associe toutes les questions retenues à des cases, sans modifier la grille tant que vous ne la confirmez pas.' : 'Cette proposition pose chaque attribut actif sur une case contenant un challenge. Rien n’est enregistré avant confirmation.'}</p>
		{#if isChallenge}
			<section class="dispatch-grid" style={`--columns:${config.columns}`} aria-label="Prévisualisation des challenges">{#each Array(config.rows * config.columns) as _, position}{@const assignment = challengeAssignments.find((item) => item.position === position)}{@const question = assignment ? questions.find((item) => item.id === assignment.question_id) : null}<article class:empty={!assignment}><span>{coordinateFor(position)}</span>{#if question}<strong>Niv. {question.level}</strong><small>{question.question}</small>{:else}<em>Case vide</em>{/if}</article>{/each}</section>
		{:else if !activeAttributes.length}<section class="empty-state"><h3>Aucun attribut actif</h3><p>Ajoutez au moins un vol ou un lot avant de lancer une attribution.</p></section>
		{:else}<section class="assignment-list" aria-label="Prévisualisation des attributs">{#each shuffledAttributes as item}<article>{#if item.attribute.type === 'prize' && item.attribute.image}<img src={assetUrl(item.attribute.image)} alt="" />{/if}<div><span class:steal={item.attribute.type === 'steal'} class="kind">{item.attribute.type === 'steal' ? 'VOL' : 'LOT'}</span><strong>{item.attribute.type === 'steal' ? 'Vol' : item.attribute.name}</strong></div><span class="target">Case {item.cell.name}</span></article>{/each}</section>{/if}
		{#if errorMessage}<p class="error" role="alert">{errorMessage}</p>{/if}
		<div class="actions">{#if isConfirming}<p class="confirmation" role="status">La répartition affichée sera figée et enregistrée. Vous pourrez encore relancer tant que vous n’avez pas confirmé.</p>{/if}<div class="buttons"><button class="secondary" type="button" disabled={isSaving} onclick={randomize}>Relancer le tirage</button>{#if isConfirming}<button class="primary" type="button" disabled={isSaving || (!isChallenge && !activeAttributes.length)} onclick={() => void save()}>{isSaving ? 'Enregistrement…' : 'Confirmer et enregistrer'}</button>{:else}<button class="primary" type="button" disabled={!isChallenge && !activeAttributes.length} onclick={() => isConfirming = true}>Continuer</button>{/if}</div></div>
	</dialog>
</div>

<style>
	.backdrop{position:fixed;z-index:30;inset:0;display:grid;place-items:center;padding:1rem;background:rgba(2,6,23,.72);backdrop-filter:blur(6px)}.dialog{width:min(100%,62rem);max-height:calc(100dvh - 2rem);overflow:auto;border:1px solid #475569;border-radius:1rem;padding:clamp(1.25rem,4vw,2rem);background:#1e293b;color:#f8fafc;box-shadow:0 1.5rem 5rem rgba(0,0,0,.45)}header{display:flex;justify-content:space-between;gap:1rem}.eyebrow{margin:0 0 .45rem;color:#c4b5fd;font-size:.7rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}h2,h3,p{margin:0}h2{font-size:1.55rem;letter-spacing:-.045em}.close{width:2.75rem;min-height:2.75rem;border:1px solid #475569;border-radius:.65rem;background:transparent;color:#cbd5e1;cursor:pointer;font:inherit;font-size:1.6rem}.intro{max-width:45rem;margin:1rem 0 1.25rem;color:#cbd5e1;font-size:.86rem;line-height:1.55}.dispatch-grid{display:grid;grid-template-columns:repeat(var(--columns,6),minmax(0,1fr));gap:.45rem}.dispatch-grid article{display:flex;min-height:5.4rem;flex-direction:column;border:1px solid rgba(124,58,237,.58);border-radius:.55rem;padding:.45rem;background:rgba(124,58,237,.11)}.dispatch-grid article.empty{border-color:#475569;background:#0f172a}.dispatch-grid span{color:#c4b5fd;font-size:.68rem;font-weight:850}.dispatch-grid strong{margin-top:.45rem;color:#ddd6fe;font-size:.68rem}.dispatch-grid small{display:-webkit-box;line-clamp:2;margin-top:.2rem;overflow:hidden;color:#e2e8f0;font-size:.68rem;line-height:1.3;-webkit-box-orient:vertical;-webkit-line-clamp:2}.dispatch-grid em{margin:auto 0;color:#64748b;font-size:.68rem;font-style:normal}.assignment-list{display:grid;gap:.55rem}.assignment-list article{display:flex;align-items:center;justify-content:space-between;gap:1rem;border:1px solid #334155;border-radius:.65rem;padding:.75rem;background:#17213a}.assignment-list img{width:2.75rem;height:2.75rem;flex:none;border:1px solid #475569;border-radius:.5rem;object-fit:cover}.kind,strong{display:block}.kind{margin-bottom:.25rem;color:#fbbf24;font-size:.63rem;font-weight:850;letter-spacing:.1em}.kind.steal{color:#fda4af}.assignment-list strong{font-size:.84rem}.target{margin-left:auto;border:1px solid rgba(56,189,248,.45);border-radius:999px;padding:.3rem .55rem;background:rgba(56,189,248,.1);color:#bae6fd;font-size:.73rem;font-weight:750}.empty-state{border:1px dashed #475569;border-radius:.7rem;padding:1.4rem;text-align:center}.empty-state h3{font-size:1rem}.empty-state p{margin-top:.45rem;color:#94a3b8;font-size:.83rem}.error{margin:1rem 0;color:#fecaca;font-size:.82rem}.actions{margin-top:1.25rem;border-top:1px solid #334155;padding-top:1rem}.confirmation{margin-bottom:.8rem;border:1px solid rgba(245,158,11,.48);border-radius:.6rem;padding:.7rem;background:rgba(245,158,11,.1);color:#fde68a;font-size:.8rem;line-height:1.45}.buttons{display:flex;justify-content:flex-end;gap:.7rem}.buttons button{min-height:2.8rem;border-radius:.6rem;padding:.65rem .95rem;cursor:pointer;font:inherit;font-size:.82rem;font-weight:800}.secondary{border:1px solid #475569;background:transparent;color:#cbd5e1}.primary{border:0;background:#7c3aed;color:#fff}.secondary:hover{border-color:#94a3b8;color:#f8fafc}.primary:hover{background:#8b5cf6}.close:disabled,.buttons button:disabled{cursor:not-allowed;opacity:.55}.close:focus-visible,.buttons button:focus-visible{outline:3px solid rgba(167,139,250,.5);outline-offset:3px}@media(max-width:700px){.dispatch-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.buttons{flex-direction:column-reverse}.buttons button{width:100%}}@media(max-width:430px){.dispatch-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.assignment-list article{align-items:flex-start;flex-wrap:wrap}.target{margin-left:0}}
</style>
