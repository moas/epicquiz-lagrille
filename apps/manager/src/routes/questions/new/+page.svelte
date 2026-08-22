<script lang="ts">
	import { goto } from '$app/navigation';
	import { createQuestion } from '$lib/episodes-api';

	type DraftAnswer = { id: number; answer: string; is_correct: boolean };

	let label = $state('');
	let level = $state('1');
	let tagText = $state('');
	let reason = $state('');
	let answers = $state<DraftAnswer[]>([
		{ id: 1, answer: '', is_correct: true },
		{ id: 2, answer: '', is_correct: false }
	]);
	let nextAnswerId = 3;
	let error = $state('');
	let isSaving = $state(false);

	function addAnswer() {
		answers = [...answers, { id: nextAnswerId++, answer: '', is_correct: false }];
	}

	function removeAnswer(id: number) {
		if (answers.length <= 2) return;
		answers = answers.filter((answer) => answer.id !== id);
	}

	function toggleCorrect(id: number) {
		answers = answers.map((answer) => answer.id === id ? { ...answer, is_correct: !answer.is_correct } : answer);
	}

	async function submit() {
		const validAnswers = answers.map((answer) => ({ ...answer, answer: answer.answer.trim() })).filter((answer) => answer.answer);
		if (!label.trim()) { error = 'Saisissez l’intitulé de la question.'; return; }
		if (validAnswers.length < 2) { error = 'Ajoutez au moins deux propositions.'; return; }
		if (!validAnswers.some((answer) => answer.is_correct)) { error = 'Indiquez au moins une bonne réponse.'; return; }

		isSaving = true;
		error = '';
		try {
			const question = await createQuestion({
				question: label.trim(),
				level: Number(level),
				tags: [...new Set(tagText.split(',').map((tag) => tag.trim()).filter(Boolean))],
				reason: reason.trim(),
				answers: validAnswers.map(({ answer, is_correct }) => ({ answer, is_correct }))
			});
			await goto(`/questions/${question.id}`);
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Impossible de créer cette question.';
			isSaving = false;
		}
	}
</script>

<svelte:head><title>Ajouter une question · EpicQuiz</title></svelte:head>

<main>
	<a class="back" href="/questions">← Retour à la bibliothèque</a>
	<header><p class="eyebrow">Base de connaissance</p><h1>Ajouter une question</h1><p>Composez la question, ses réponses et une justification utile aux animateurs.</p></header>
	<form onsubmit={(event) => { event.preventDefault(); void submit(); }}>
		<section class="form-card"><label for="question">Question<textarea id="question" bind:value={label} rows="3" maxlength="160" placeholder="Quelle question souhaitez-vous poser ?" disabled={isSaving}></textarea></label><div class="fields"><label for="level">Niveau<select id="level" bind:value={level} disabled={isSaving}>{#each [1, 2, 3, 4, 5] as value}<option value={String(value)}>Niveau {value}</option>{/each}</select></label><label for="tags">Tags <span>séparés par une virgule</span><input id="tags" bind:value={tagText} placeholder="Histoire, Europe, culture" disabled={isSaving} /></label></div><label for="reason">Justification <span>optionnelle</span><textarea id="reason" bind:value={reason} rows="3" placeholder="Pourquoi la bonne réponse est-elle correcte ?" disabled={isSaving}></textarea></label></section>

		<section class="answers" aria-labelledby="answers-title"><div class="answers-heading"><div><p class="eyebrow">Réponses proposées</p><h2 id="answers-title">Choix de réponse</h2><p>Choisissez au moins une bonne réponse.</p></div><button type="button" class="secondary" disabled={isSaving} onclick={addAnswer}>Ajouter une proposition</button></div><div class="answer-list">{#each answers as answer, index (answer.id)}<div class="answer-row"><label for={`answer-${answer.id}`}>Proposition {index + 1}<input id={`answer-${answer.id}`} bind:value={answer.answer} placeholder={`Réponse ${index + 1}`} disabled={isSaving} /></label><button type="button" class:correct={answer.is_correct} class="correct-button" disabled={isSaving} onclick={() => toggleCorrect(answer.id)}>{answer.is_correct ? 'Bonne réponse' : 'Marquer correcte'}</button><button type="button" class="remove" disabled={isSaving || answers.length <= 2} aria-label={`Supprimer la proposition ${index + 1}`} onclick={() => removeAnswer(answer.id)}>Supprimer</button></div>{/each}</div></section>
		{#if error}<p class="error" role="alert">{error}</p>{/if}
		<div class="actions"><a href="/questions">Annuler</a><button type="submit" disabled={isSaving}>{isSaving ? 'Création…' : 'Créer la question'}</button></div>
	</form>
</main>

<style>
	:global(*){box-sizing:border-box}:global(body){margin:0;background:#0f172a;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,sans-serif}main{width:min(100%,58rem);min-height:100dvh;margin:auto;padding:clamp(1.25rem,4vw,3rem)}.back{color:#c4b5fd;font-size:.85rem;font-weight:750;text-decoration:none}header{margin:3rem 0 2rem}.eyebrow{margin:0 0 .6rem;color:#c4b5fd;font-size:.7rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}h1{margin:0;color:#f8fafc;font-size:clamp(2.4rem,5vw,4.2rem);letter-spacing:-.065em}header>p:last-child{max-width:42rem;margin:1rem 0 0;color:#cbd5e1;line-height:1.6}.form-card,.answers{display:grid;gap:1.2rem;border:1px solid #334155;border-radius:1rem;padding:clamp(1rem,3vw,1.5rem);background:#1e293b}label{display:block;color:#f8fafc;font-size:.8rem;font-weight:750}label>span{color:#94a3b8;font-weight:500}textarea,input,select{width:100%;margin-top:.45rem;border:1px solid #475569;border-radius:.6rem;padding:.7rem;background:#0f172a;color:#f8fafc;font:inherit;font-weight:500}textarea{min-height:5.4rem;resize:vertical;line-height:1.5}.fields{display:grid;grid-template-columns:10rem 1fr;gap:1rem}.answers{margin-top:1rem}.answers-heading{display:flex;justify-content:space-between;gap:1rem;align-items:start}.answers-heading h2{margin:0;color:#f8fafc;font-size:1.25rem}.answers-heading p:last-child{margin:.4rem 0 0;color:#94a3b8;font-size:.82rem}.answers button,.actions button,.actions a{display:inline-flex;min-height:2.7rem;align-items:center;justify-content:center;border:0;border-radius:.6rem;padding:.6rem .9rem;background:#7c3aed;color:#fff;cursor:pointer;font:inherit;font-size:.8rem;font-weight:800;text-decoration:none}.answers .secondary{border:1px solid #475569;background:#17213a;color:#ddd6fe}.answer-list{display:grid;gap:.7rem}.answer-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:.65rem;align-items:end;border-top:1px solid #334155;padding-top:.9rem}.answer-row:first-child{border-top:0;padding-top:0}.answer-row label{color:#cbd5e1;font-size:.72rem}.correct-button{border:1px solid #475569!important;background:#17213a!important;color:#cbd5e1!important}.correct-button.correct{border-color:rgba(34,197,94,.6)!important;background:rgba(34,197,94,.12)!important;color:#86efac!important}.remove{border:1px solid rgba(239,68,68,.55)!important;background:transparent!important;color:#fca5a5!important}.answers button:disabled,.actions button:disabled{cursor:not-allowed;opacity:.55}.error{margin:1rem 0 0;border:1px solid rgba(239,68,68,.55);border-radius:.7rem;padding:.85rem 1rem;background:rgba(127,29,29,.2);color:#fecaca}.actions{display:flex;justify-content:flex-end;gap:.7rem;margin-top:1.4rem}.actions a{border:1px solid #475569;background:transparent;color:#cbd5e1}.back:focus-visible,textarea:focus-visible,input:focus-visible,select:focus-visible,button:focus-visible,.actions a:focus-visible{outline:3px solid #a78bfa;outline-offset:3px}@media(max-width:600px){header{margin:2rem 0}.fields,.answer-row{grid-template-columns:1fr}.answers-heading{flex-direction:column}.answers-heading button{width:100%}.actions{flex-direction:column-reverse}.actions>*{width:100%}}
</style>
