<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { createQuestionProposition, deleteQuestion, getQuestion, type Question } from '$lib/episodes-api';
	import type { PageProps } from './$types';

	let { params }: PageProps = $props();
	let question = $state<Question | null>(null);
	let error = $state('');
	let isLoading = $state(true);
	let isDeleting = $state(false);
	let proposition = $state('');
	let isCorrect = $state(false);
	let isAddingProposition = $state(false);

	onMount(async () => {
		try {
			question = await getQuestion(params.id);
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Impossible de charger cette question.';
		} finally {
			isLoading = false;
		}
	});

	async function remove() {
		if (!question || !confirm(`Supprimer définitivement « ${question.question} » ?`)) return;
		isDeleting = true;
		error = '';
		try {
			await deleteQuestion(question.id);
			await goto('/questions');
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Impossible de supprimer cette question.';
			isDeleting = false;
		}
	}

	async function addProposition() {
		if (!question || !proposition.trim()) {
			error = 'Saisissez une proposition avant de l’ajouter.';
			return;
		}
		isAddingProposition = true;
		error = '';
		try {
			const answer = await createQuestionProposition(question.id, {
				answer: proposition.trim(),
				is_correct: isCorrect
			});
			question = {
				...question,
				answers: question.answers.some((item) => item.id === answer.id)
					? question.answers.map((item) => item.id === answer.id ? answer : item)
					: [...question.answers, answer]
			};
			proposition = '';
			isCorrect = false;
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Impossible d’ajouter cette proposition.';
		} finally {
			isAddingProposition = false;
		}
	}
</script>

<svelte:head><title>{question ? `${question.question} · EpicQuiz` : 'Question · EpicQuiz'}</title></svelte:head>

<main>
	<a class="back" href="/questions">← Bibliothèque de questions</a>
	{#if isLoading}<section class="status" role="status">Chargement de la question…</section>
	{:else if error && !question}<section class="error" role="alert"><strong>Impossible d’ouvrir la question.</strong><p>{error}</p></section>
	{:else if question}
		<header><div><p class="eyebrow">Question · Niveau {question.level}</p><h1>{question.question}</h1><div class="tags">{#each question.tags as tag}<span>{tag}</span>{:else}<span class="muted">Sans tag</span>{/each}</div></div><div class="actions"><a class="edit" href={`/questions/${question.id}/edit`}>Modifier</a><button class="delete" type="button" disabled={isDeleting} onclick={() => void remove()}>{isDeleting ? 'Suppression…' : 'Supprimer'}</button></div></header>

		{#if error}<p class="error" role="alert">{error}</p>{/if}
		<div class="layout">
			<section class="panel answers" aria-labelledby="answers-title"><div class="section-heading"><div><p class="eyebrow">Réponses proposées</p><h2 id="answers-title">Choix de réponse</h2></div><span>{question.answers.length} proposition{question.answers.length > 1 ? 's' : ''}</span></div><form class="add-answer" onsubmit={(event) => { event.preventDefault(); void addProposition(); }}><label for="new-proposition">Nouvelle proposition<input id="new-proposition" bind:value={proposition} placeholder="Saisir une réponse possible" disabled={isAddingProposition} /></label><label class="correct-toggle"><input type="checkbox" bind:checked={isCorrect} disabled={isAddingProposition} /><span>Bonne réponse</span></label><button type="submit" disabled={isAddingProposition}>{isAddingProposition ? 'Ajout…' : 'Ajouter'}</button></form><ol>{#each question.answers as answer}<li class:correct={answer.is_correct}><span class="marker" aria-hidden="true">{answer.is_correct ? '✓' : '·'}</span><span>{answer.answer}</span>{#if answer.is_correct}<b>Bonne réponse</b>{/if}</li>{:else}<li class="empty">Aucune proposition associée.</li>{/each}</ol></section>
			<aside class="side"><section class="panel"><p class="eyebrow">Disponibilité</p><strong class:inactive={!question.is_active} class="availability">{question.is_active ? 'Utilisable' : 'Inactive'}</strong><p class="helper">Cette question est {question.is_active ? 'disponible' : 'masquée'} pour la préparation des épisodes.</p></section><section class="panel"><p class="eyebrow">Justification</p><p class:empty={!question.reason} class="reason">{question.reason || 'Aucune justification renseignée.'}</p></section></aside>
		</div>
	{/if}
</main>

<style>
	:global(*){box-sizing:border-box}:global(body){margin:0;background:#0f172a;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,sans-serif}main{width:min(100%,72rem);min-height:100dvh;margin:auto;padding:clamp(1.25rem,4vw,3rem)}.back{color:#c4b5fd;font-size:.85rem;font-weight:750;text-decoration:none}header{display:flex;justify-content:space-between;gap:2rem;margin:3rem 0}.eyebrow{margin:0 0 .55rem;color:#c4b5fd;font-size:.7rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}h1{max-width:52rem;margin:0;color:#f8fafc;font-size:clamp(2.3rem,5.5vw,4.5rem);line-height:1;letter-spacing:-.065em}.tags{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:1.25rem}.tags span{border-radius:999px;padding:.36rem .58rem;background:#334155;color:#cbd5e1;font-size:.74rem;font-weight:700}.tags .muted{background:transparent;color:#94a3b8}.actions{display:flex;align-items:start;gap:.65rem}.actions a,.actions button{display:inline-flex;min-height:2.8rem;align-items:center;justify-content:center;border-radius:.6rem;padding:.65rem 1rem;cursor:pointer;font:inherit;font-size:.84rem;font-weight:800;text-decoration:none}.edit{background:#7c3aed;color:#fff}.delete{border:1px solid rgba(239,68,68,.6);background:transparent;color:#fca5a5}.delete:disabled{cursor:not-allowed;opacity:.55}.layout{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(16rem,.8fr);gap:1rem}.panel{border:1px solid #334155;border-radius:1rem;padding:1.25rem;background:#1e293b}.section-heading{display:flex;justify-content:space-between;gap:1rem;align-items:start}.section-heading h2{margin:0;color:#f8fafc;font-size:1.25rem;letter-spacing:-.03em}.section-heading>span{border-radius:999px;padding:.35rem .55rem;background:#334155;color:#cbd5e1;font-size:.72rem;font-weight:750}.add-answer{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:.65rem;align-items:end;margin-top:1.25rem;border:1px solid #334155;border-radius:.75rem;padding:.8rem;background:#17213a}.add-answer label{color:#cbd5e1;font-size:.72rem;font-weight:750}.add-answer input{display:block;width:100%;min-height:2.55rem;margin-top:.35rem;border:1px solid #475569;border-radius:.5rem;padding:0 .65rem;background:#0f172a;color:#f8fafc;font:inherit}.correct-toggle{display:flex;min-height:2.55rem;align-items:center;gap:.45rem;white-space:nowrap}.correct-toggle input{width:1rem;min-height:auto;margin:0;accent-color:#22c55e}.add-answer button{min-height:2.55rem;border:0;border-radius:.5rem;padding:.55rem .8rem;background:#7c3aed;color:#fff;cursor:pointer;font:inherit;font-size:.78rem;font-weight:800}.add-answer button:disabled{cursor:not-allowed;opacity:.6}ol{display:grid;gap:.65rem;margin:1.4rem 0 0;padding:0;list-style:none}li{display:grid;grid-template-columns:1.25rem 1fr auto;gap:.7rem;align-items:center;border:1px solid #334155;border-radius:.7rem;padding:.85rem;background:#17213a;color:#cbd5e1;font-size:.9rem}.marker{display:grid;width:1.2rem;height:1.2rem;place-items:center;border-radius:50%;background:#334155;color:#94a3b8;font-weight:900}.correct{border-color:rgba(34,197,94,.45);background:rgba(34,197,94,.08);color:#dcfce7}.correct .marker{background:#22c55e;color:#052e16}.correct b{color:#86efac;font-size:.72rem}.empty{display:block;color:#94a3b8;text-align:center}.side{display:grid;align-content:start;gap:1rem}.availability{display:inline-flex;border-radius:999px;padding:.4rem .65rem;background:rgba(34,197,94,.13);color:#86efac;font-size:.78rem}.availability.inactive{background:#334155;color:#cbd5e1}.helper,.reason{margin:.85rem 0 0;color:#cbd5e1;font-size:.84rem;line-height:1.6}.reason.empty{color:#94a3b8;font-style:italic}.status,.error{margin-top:4rem;border:1px solid #334155;border-radius:1rem;padding:1.25rem;background:#17213a;color:#cbd5e1;text-align:center}.error{border-color:rgba(239,68,68,.5);color:#fecaca}.error p{margin:.5rem 0 0}.back:focus-visible,.actions a:focus-visible,.actions button:focus-visible,.add-answer input:focus-visible,.add-answer button:focus-visible{outline:3px solid #a78bfa;outline-offset:3px}@media(max-width:700px){header{flex-direction:column;margin:2rem 0}.actions{width:100%}.actions>*{flex:1}.layout{grid-template-columns:1fr}.add-answer{grid-template-columns:1fr}.correct-toggle{min-height:1.5rem}.add-answer button{width:100%}}
</style>
