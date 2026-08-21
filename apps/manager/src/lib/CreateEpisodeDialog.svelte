<script lang="ts">
	import { ApiError, createEpisode, type Episode } from '$lib/episodes-api';

	let { onclose, oncreated }: { onclose: () => void; oncreated: (episode: Episode) => void } = $props();

	let title = $state('');
	let timeSlot = $state(10);
	let isActive = $state(true);
	let isSaving = $state(false);
	let formError = $state('');
	let titleError = $state('');
	let timeSlotError = $state('');
	let titleInput: HTMLInputElement;

	function validate() {
		titleError = title.trim() ? '' : 'Indiquez un titre pour cet épisode.';
		timeSlotError = Number.isInteger(timeSlot) && timeSlot >= 1 ? '' : 'La durée doit être d’au moins 1 seconde.';
		return !titleError && !timeSlotError;
	}

	async function submit() {
		formError = '';
		if (!validate()) return;

		isSaving = true;
		try {
			const episode = await createEpisode({ title: title.trim(), time_slot: timeSlot, is_active: isActive });
			oncreated(episode);
		} catch (error) {
			if (error instanceof ApiError) {
				titleError = error.fieldErrors.title ?? '';
				timeSlotError = error.fieldErrors.time_slot ?? '';
				formError = error.fieldErrors.non_field_errors ?? error.message;
			} else {
				formError = 'Impossible d’enregistrer cet épisode. Réessayez dans un instant.';
			}
		} finally {
			isSaving = false;
		}
	}

	$effect(() => {
		titleInput?.focus();
	});
</script>

<div class="backdrop" role="presentation" onclick={(event) => event.currentTarget === event.target && !isSaving && onclose()}>
	<dialog class="dialog" open aria-labelledby="create-episode-title">
		<div class="dialog-heading">
			<div><p class="eyebrow">Nouvel épisode</p><h2 id="create-episode-title">Préparer une nouvelle session</h2></div>
			<button class="close" type="button" aria-label="Fermer" disabled={isSaving} onclick={onclose}>×</button>
		</div>
		<p class="intro">Vous pourrez configurer la grille et les participants juste après la création.</p>

		<form onsubmit={(event) => { event.preventDefault(); void submit(); }}>
			<div class="field">
				<label for="episode-title">Titre de l’épisode</label>
				<input bind:this={titleInput} id="episode-title" bind:value={title} aria-invalid={Boolean(titleError)} aria-describedby={titleError ? 'episode-title-error' : undefined} maxlength="255" placeholder="Ex. Épisode 12 — Finale" disabled={isSaving} onblur={validate} />
				{#if titleError}<p class="field-error" id="episode-title-error" role="alert">{titleError}</p>{/if}
			</div>
			<div class="field">
				<label for="episode-time-slot">Durée par question <span>(secondes)</span></label>
				<input id="episode-time-slot" bind:value={timeSlot} aria-invalid={Boolean(timeSlotError)} aria-describedby={timeSlotError ? 'episode-time-slot-error' : undefined} type="number" min="1" step="1" disabled={isSaving} onblur={validate} />
				{#if timeSlotError}<p class="field-error" id="episode-time-slot-error" role="alert">{timeSlotError}</p>{/if}
			</div>
			<label class="toggle"><input type="checkbox" bind:checked={isActive} disabled={isSaving} /><span aria-hidden="true"></span><span><strong>Épisode actif</strong><small>Il sera disponible pour la préparation.</small></span></label>
			{#if formError}<p class="form-error" role="alert">{formError}</p>{/if}
			<div class="actions"><button type="button" class="cancel" disabled={isSaving} onclick={onclose}>Annuler</button><button class="submit" type="submit" disabled={isSaving}>{isSaving ? 'Création…' : 'Créer et configurer'}</button></div>
		</form>
	</dialog>
</div>

<style>
	.backdrop { position:fixed; z-index:10; inset:0; display:grid; place-items:center; padding:1rem; background:rgba(2,6,23,.68); backdrop-filter:blur(6px); }
	.dialog { width:min(100%,32rem); border:1px solid #475569; border-radius:1rem; padding:clamp(1.25rem,4vw,2rem); background:#1e293b; box-shadow:0 1.5rem 5rem rgba(0,0,0,.42); }
	.dialog-heading { display:flex; justify-content:space-between; gap:1rem; }.eyebrow { margin:0 0 .45rem; color:#c4b5fd; font-size:.7rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }.dialog h2 { margin:0; color:#f8fafc; font-size:1.55rem; letter-spacing:-.045em; }.close { width:2.75rem; height:2.75rem; flex:none; border:1px solid #475569; border-radius:.65rem; background:transparent; color:#cbd5e1; cursor:pointer; font-size:1.6rem; line-height:1; }.close:hover { color:#f8fafc; border-color:#94a3b8; }.intro { margin:1rem 0 1.5rem; color:#cbd5e1; font-size:.9rem; line-height:1.55; }.field { margin-bottom:1.15rem; }.field label { display:block; margin-bottom:.45rem; color:#f8fafc; font-size:.85rem; font-weight:750; }.field label span,.toggle small { color:#94a3b8; font-weight:500; }.field input { width:100%; min-height:2.8rem; border:1px solid #475569; border-radius:.6rem; padding:0 .75rem; background:#0f172a; color:#f8fafc; font:inherit; }.field input[aria-invalid='true'] { border-color:#ef4444; }.field input:focus,.toggle input:focus-visible + span { outline:3px solid rgba(167,139,250,.32); outline-offset:2px; border-color:#a78bfa; }.field-error,.form-error { margin:.45rem 0 0; color:#fecaca; font-size:.8rem; line-height:1.4; }.toggle { display:flex; align-items:center; gap:.75rem; margin-top:1.4rem; cursor:pointer; }.toggle input { position:absolute; opacity:0; }.toggle > span:first-of-type { position:relative; width:2.6rem; height:1.5rem; flex:none; border-radius:999px; background:#475569; transition:background 180ms ease; }.toggle > span:first-of-type::after { position:absolute; top:.2rem; left:.2rem; width:1.1rem; height:1.1rem; border-radius:50%; background:#f8fafc; content:''; transition:transform 180ms ease; }.toggle input:checked + span { background:#7c3aed; }.toggle input:checked + span::after { transform:translateX(1.1rem); }.toggle strong,.toggle small { display:block; }.toggle strong { color:#f8fafc; font-size:.85rem; }.toggle small { margin-top:.16rem; font-size:.76rem; }.actions { display:flex; justify-content:flex-end; gap:.7rem; margin-top:1.7rem; }.actions button { min-height:2.8rem; border-radius:.6rem; padding:.7rem 1rem; cursor:pointer; font:inherit; font-size:.85rem; font-weight:750; }.cancel { border:1px solid #475569; background:transparent; color:#cbd5e1; }.submit { border:1px solid #7c3aed; background:#7c3aed; color:#fff; }.cancel:hover { border-color:#94a3b8; color:#f8fafc; }.submit:hover { background:#8b5cf6; }.actions button:disabled,.close:disabled,.toggle:has(input:disabled) { cursor:not-allowed; opacity:.6; }.close:focus-visible,.actions button:focus-visible { outline:3px solid #a78bfa; outline-offset:3px; } @media (max-width:420px) { .actions { flex-direction:column-reverse; }.actions button { width:100%; } }
</style>
