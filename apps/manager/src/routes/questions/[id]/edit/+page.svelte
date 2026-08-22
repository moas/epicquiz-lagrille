<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { getQuestion, updateQuestion, type Question } from '$lib/episodes-api';
	import type { PageProps } from './$types';

	let { params }: PageProps = $props();
	let source = $state<Question | null>(null);
	let label = $state('');
	let level = $state('1');
	let tagText = $state('');
	let reason = $state('');
	let isActive = $state(true);
	let error = $state('');
	let isLoading = $state(true);
	let isSaving = $state(false);

	onMount(async () => {
		try {
			source = await getQuestion(params.id);
			label = source.question;
			level = String(source.level);
			tagText = source.tags.join(', ');
			reason = source.reason ?? '';
			isActive = source.is_active;
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Impossible de charger cette question.';
		} finally {
			isLoading = false;
		}
	});

	async function submit() {
		if (!source || !label.trim()) {
			error = 'Saisissez l’intitulé de la question.';
			return;
		}
		isSaving = true;
		error = '';
		try {
			await updateQuestion(source.id, {
				question: label.trim(),
				level: Number(level),
				tags: [...new Set(tagText.split(',').map((tag) => tag.trim()).filter(Boolean))],
				reason: reason.trim(),
				is_active: isActive
			});
			await goto(`/questions/${source.id}`);
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Impossible d’enregistrer cette question.';
			isSaving = false;
		}
	}
</script>

<svelte:head><title>Modifier une question · EpicQuiz</title></svelte:head>

<main>
	<a class="back" href={source ? `/questions/${source.id}` : '/questions'}>← Annuler et revenir à la question</a>
	{#if isLoading}<section class="status" role="status">Chargement de la question…</section>
	{:else if !source}<section class="error" role="alert">{error}</section>
	{:else}
		<header><p class="eyebrow">Bibliothèque de questions</p><h1>Modifier la question</h1><p>Modifiez les informations, la justification et la disponibilité. Les propositions restent inchangées.</p></header>
		<form onsubmit={(event) => { event.preventDefault(); void submit(); }}>
			<section class="form-card"><label for="question">Question<textarea id="question" bind:value={label} rows="3" maxlength="160" disabled={isSaving}></textarea></label><div class="fields"><label for="level">Niveau<select id="level" bind:value={level} disabled={isSaving}>{#each [1, 2, 3, 4, 5] as value}<option value={String(value)}>Niveau {value}</option>{/each}</select></label><label for="tags">Tags <span>séparés par une virgule</span><input id="tags" bind:value={tagText} placeholder="Histoire, Europe, culture" disabled={isSaving} /></label></div><label for="reason">Justification <span>optionnelle</span><textarea id="reason" bind:value={reason} rows="4" placeholder="Expliquez pourquoi cette réponse est correcte…" disabled={isSaving}></textarea><small class="field-help">Laissez ce champ vide pour supprimer la justification.</small></label><label class="toggle"><input type="checkbox" bind:checked={isActive} disabled={isSaving} /><span aria-hidden="true"></span><span><strong>Question disponible</strong><small>Elle peut être utilisée dans la configuration d’un épisode.</small></span></label></section>
			{#if error}<p class="error" role="alert">{error}</p>{/if}
			<div class="actions"><a class="cancel" href={`/questions/${source.id}`}>Annuler</a><button type="submit" disabled={isSaving}>{isSaving ? 'Enregistrement…' : 'Enregistrer les modifications'}</button></div>
		</form>
	{/if}
</main>

<style>
	:global(*){box-sizing:border-box}:global(body){margin:0;background:#0f172a;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,sans-serif}main{width:min(100%,52rem);min-height:100dvh;margin:auto;padding:clamp(1.25rem,4vw,3rem)}.back{color:#c4b5fd;font-size:.85rem;font-weight:750;text-decoration:none}header{margin:3rem 0 2rem}.eyebrow{margin:0 0 .6rem;color:#c4b5fd;font-size:.7rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}h1{margin:0;color:#f8fafc;font-size:clamp(2.3rem,5vw,4rem);letter-spacing:-.065em}header>p:last-child{max-width:38rem;margin:1rem 0 0;color:#cbd5e1;line-height:1.6}.form-card{display:grid;gap:1.2rem;border:1px solid #334155;border-radius:1rem;padding:clamp(1rem,3vw,1.5rem);background:#1e293b}label{display:block;color:#f8fafc;font-size:.8rem;font-weight:750}label>span{color:#94a3b8;font-weight:500}textarea,input,select{width:100%;margin-top:.45rem;border:1px solid #475569;border-radius:.6rem;padding:.7rem;background:#0f172a;color:#f8fafc;font:inherit;font-weight:500}textarea{min-height:6rem;resize:vertical;line-height:1.5}.field-help{display:block;margin-top:.35rem;color:#94a3b8;font-size:.74rem;font-weight:500;line-height:1.4}.fields{display:grid;grid-template-columns:10rem 1fr;gap:1rem}.toggle{display:flex;align-items:center;gap:.75rem;margin-top:.2rem;cursor:pointer}.toggle input{position:absolute;width:auto;opacity:0}.toggle>span:first-of-type{position:relative;width:2.6rem;height:1.5rem;flex:none;margin:0;border-radius:999px;background:#475569}.toggle>span:first-of-type:after{position:absolute;top:.2rem;left:.2rem;width:1.1rem;height:1.1rem;border-radius:50%;background:#f8fafc;content:'';transition:transform 180ms ease}.toggle input:checked+span{background:#7c3aed}.toggle input:checked+span:after{transform:translateX(1.1rem)}.toggle strong,.toggle small{display:block}.toggle small{margin-top:.15rem;color:#94a3b8;font-size:.76rem;font-weight:500;line-height:1.45}.actions{display:flex;justify-content:flex-end;gap:.7rem;margin-top:1.4rem}.actions a,.actions button{display:inline-flex;min-height:2.8rem;align-items:center;justify-content:center;border:0;border-radius:.6rem;padding:.65rem 1rem;background:#7c3aed;color:#fff;cursor:pointer;font:inherit;font-size:.84rem;font-weight:800;text-decoration:none}.actions .cancel{border:1px solid #475569;background:transparent;color:#cbd5e1}.actions button:disabled{cursor:not-allowed;opacity:.6}.error,.status{margin-top:1rem;border:1px solid rgba(239,68,68,.55);border-radius:.7rem;padding:.85rem 1rem;background:rgba(127,29,29,.2);color:#fecaca}.status{margin-top:4rem;border-color:#334155;background:#17213a;color:#cbd5e1;text-align:center}.back:focus-visible,textarea:focus-visible,input:focus-visible,select:focus-visible,.actions a:focus-visible,.actions button:focus-visible,.toggle input:focus-visible+span{outline:3px solid #a78bfa;outline-offset:3px}@media(max-width:600px){header{margin:2rem 0}.fields{grid-template-columns:1fr}.actions{flex-direction:column-reverse}.actions>*{width:100%}}
</style>
