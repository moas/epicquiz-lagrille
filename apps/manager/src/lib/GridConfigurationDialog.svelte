<script lang="ts">
	import { ApiError, updateEpisode, type Episode, type GridConfig } from '$lib/episodes-api';

	let { episode, onclose, onconfigured }: { episode: Episode; onclose: () => void; onconfigured: (episode: Episode) => void } = $props();

	function initialConfig() {
		return episode.metadata.grid_config;
	}

	const existing = initialConfig();
	let rows = $state(existing?.rows ?? 5);
	let columns = $state(existing?.columns ?? 5);
	let emptyCellCount = $state(existing?.empty_cell_count ?? 0);
	let distribution = $state<Record<string, number>>(existing?.point_distribution ?? { '100': 9, '200': 8, '300': 8 });
	let isSaving = $state(false);
	let formError = $state('');
	let distributionError = $state('');
	let previousPlayableCells = $state(0);
	let hasInitialized = $state(false);

	const cellCount = $derived(rows * columns);
	const playableCells = $derived(cellCount - emptyCellCount);
	const distributedCells = $derived(Object.values(distribution).reduce((total, count) => total + (Number(count) || 0), 0));
	const rowPreview = $derived(createLabels(rows, true).join(', '));
	const columnPreview = $derived(createLabels(columns, false).join(', '));

	function createLabels(count: number, letters: boolean) {
		return Array.from({ length: count }, (_, index) => letters ? toAlphabeticLabel(index) : String(index + 1));
	}

	function toAlphabeticLabel(index: number) {
		let value = index + 1;
		let label = '';
		while (value > 0) {
			value -= 1;
			label = String.fromCharCode(65 + (value % 26)) + label;
			value = Math.floor(value / 26);
		}
		return label;
	}

	function distributeEvenly(total: number) {
		const base = Math.floor(total / 3);
		const remainder = total % 3;
		distribution = { '100': base + (remainder > 0 ? 1 : 0), '200': base + (remainder > 1 ? 1 : 0), '300': base };
	}

	function validate() {
		formError = '';
		if (!Number.isInteger(rows) || !Number.isInteger(columns) || rows < 1 || columns < 1) {
			formError = 'La grille doit contenir au moins une ligne et une colonne.';
			return false;
		}
		if (!Number.isInteger(emptyCellCount) || emptyCellCount < 0 || emptyCellCount >= cellCount) {
			formError = 'La grille doit conserver au moins une case jouable.';
			return false;
		}
		distributionError = distributedCells === playableCells ? '' : `Répartissez exactement ${playableCells} cases jouables (actuellement ${distributedCells}).`;
		return !distributionError;
	}

	async function save() {
		if (!validate()) return;

		isSaving = true;
		try {
			const gridConfig: GridConfig = {
				version: 1,
				rows,
				columns,
				empty_cell_count: emptyCellCount,
				point_distribution: distribution,
				coordinate_format: { x: rowPreview, y: columnPreview }
			};
			onconfigured(await updateEpisode(episode.id, { metadata: { grid_config: gridConfig } }));
		} catch (error) {
			formError = error instanceof ApiError ? error.fieldErrors.metadata ?? error.message : 'Impossible d’enregistrer la configuration.';
		} finally {
			isSaving = false;
		}
	}

	$effect(() => {
		if (emptyCellCount > cellCount - 1) emptyCellCount = Math.max(0, cellCount - 1);
		if (!hasInitialized) {
			previousPlayableCells = playableCells;
			hasInitialized = true;
			return;
		}
		if (playableCells !== previousPlayableCells) {
			distributeEvenly(playableCells);
			previousPlayableCells = playableCells;
		}
	});
</script>

<div class="backdrop" role="presentation" onclick={(event) => event.currentTarget === event.target && !isSaving && onclose()}>
	<dialog class="dialog" open aria-labelledby="grid-config-title">
		<div class="heading"><div><p class="eyebrow">Configuration</p><h2 id="grid-config-title">Préparer la grille</h2></div><button class="close" type="button" aria-label="Fermer" disabled={isSaving} onclick={onclose}>×</button></div>
		<p class="intro">Les coordonnées sont générées automatiquement : <strong>{rowPreview}</strong> et <strong>{columnPreview}</strong>.</p>
		<form onsubmit={(event) => { event.preventDefault(); void save(); }}>
			<div class="dimensions"><label for="grid-rows">Lignes<input id="grid-rows" type="number" min="1" max="99" bind:value={rows} disabled={isSaving} onblur={validate} /></label><label for="grid-columns">Colonnes<input id="grid-columns" type="number" min="1" max="99" bind:value={columns} disabled={isSaving} onblur={validate} /></label><label for="grid-empty">Cases vides<input id="grid-empty" type="number" min="0" max={Math.max(0, cellCount - 1)} bind:value={emptyCellCount} disabled={isSaving} onblur={validate} /></label></div>
			<section class="distribution" aria-labelledby="points-title"><div><h3 id="points-title">Répartition des points</h3><p>{playableCells} cases jouables à distribuer.</p></div><div class="point-inputs">{#each ['100', '200', '300'] as points}<label for={`points-${points}`}><span>{points} pts</span><input id={`points-${points}`} type="number" min="0" bind:value={distribution[points]} disabled={isSaving} onblur={validate} /></label>{/each}</div>{#if distributionError}<p class="field-error" role="alert">{distributionError}</p>{/if}</section>
			{#if formError}<p class="form-error" role="alert">{formError}</p>{/if}
			<div class="actions"><button class="cancel" type="button" disabled={isSaving} onclick={onclose}>Annuler</button><button class="submit" type="submit" disabled={isSaving}>{isSaving ? 'Enregistrement…' : 'Enregistrer la grille'}</button></div>
		</form>
	</dialog>
</div>

<style>
	.backdrop { position:fixed; z-index:20; inset:0; display:grid; place-items:center; padding:1rem; background:rgba(2,6,23,.7); backdrop-filter:blur(6px); }.dialog { width:min(100%,40rem); max-height:calc(100dvh - 2rem); overflow:auto; border:1px solid #475569; border-radius:1rem; padding:clamp(1.25rem,4vw,2rem); background:#1e293b; color:#f8fafc; box-shadow:0 1.5rem 5rem rgba(0,0,0,.42); }.heading { display:flex; justify-content:space-between; gap:1rem; }.eyebrow { margin:0 0 .45rem; color:#c4b5fd; font-size:.7rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }.heading h2 { margin:0; color:#f8fafc; font-size:1.55rem; letter-spacing:-.045em; }.close { width:2.75rem; height:2.75rem; flex:none; border:1px solid #475569; border-radius:.65rem; background:transparent; color:#cbd5e1; cursor:pointer; font-size:1.6rem; }.close:hover { border-color:#94a3b8; color:#f8fafc; }.intro { margin:1rem 0 1.5rem; color:#cbd5e1; font-size:.85rem; line-height:1.55; }.intro strong { color:#ddd6fe; font-weight:650; }.dimensions,.point-inputs { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; }.dimensions label,.point-inputs label { color:#f8fafc; font-size:.8rem; font-weight:750; }.dimensions input,.point-inputs input { width:100%; min-height:2.7rem; margin-top:.45rem; border:1px solid #475569; border-radius:.55rem; padding:0 .65rem; background:#0f172a; color:#f8fafc; font:inherit; }.dimensions input:focus,.point-inputs input:focus { border-color:#a78bfa; outline:3px solid rgba(167,139,250,.24); }.distribution { margin-top:1.5rem; border:1px solid #334155; border-radius:.8rem; padding:1rem; background:#17213a; }.distribution h3 { margin:0 0 .25rem; color:#f8fafc; font-size:.95rem; }.distribution p { margin:0 0 1rem; color:#94a3b8; font-size:.78rem; }.point-inputs label { display:flex; align-items:center; justify-content:space-between; gap:.5rem; }.point-inputs input { width:4.4rem; margin:0; }.field-error,.form-error { margin:1rem 0 0; color:#fecaca; font-size:.8rem; line-height:1.45; }.actions { display:flex; justify-content:flex-end; gap:.7rem; margin-top:1.5rem; }.actions button { min-height:2.8rem; border-radius:.6rem; padding:.7rem 1rem; cursor:pointer; font:inherit; font-size:.85rem; font-weight:750; }.cancel { border:1px solid #475569; background:transparent; color:#cbd5e1; }.submit { border:1px solid #7c3aed; background:#7c3aed; color:#fff; }.cancel:hover { border-color:#94a3b8; color:#f8fafc; }.submit:hover { background:#8b5cf6; }.actions button:disabled,.close:disabled { cursor:not-allowed; opacity:.6; }.close:focus-visible,.actions button:focus-visible { outline:3px solid #a78bfa; outline-offset:3px; } @media (max-width:520px) { .dimensions,.point-inputs { grid-template-columns:1fr; }.point-inputs label { min-height:2.75rem; }.actions { flex-direction:column-reverse; }.actions button { width:100%; } }
</style>
