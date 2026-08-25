<script lang="ts">
	import { onMount } from 'svelte';
	import {
		createPrizeAttribute,
		createStealAttribute,
		deleteSpecialAttribute,
		assetUrl,
		getPrizeAttributes,
		getStealAttributes,
		type SpecialAttribute
	} from '$lib/episodes-api';

	let { episodeId, locked = false, onclose, onchange }: { episodeId: string; locked?: boolean; onclose: () => void; onchange: (attributes: SpecialAttribute[]) => void } = $props();
	let attributes = $state<SpecialAttribute[]>([]);
	let prizeName = $state('');
	let prizeDescription = $state('');
	let prizeImage = $state<File | null>(null);
	let prizeImageInput = $state<HTMLInputElement | null>(null);
	let isLoading = $state(true);
	let isSaving = $state(false);
	let errorMessage = $state('');

	async function load() {
		isLoading = true;
		try {
			attributes = (await Promise.all([getStealAttributes(episodeId), getPrizeAttributes(episodeId)])).flat();
			onchange(attributes);
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Impossible de charger les attributs.';
		} finally { isLoading = false; }
	}

	onMount(() => { void load(); });

	async function addSteal() {
		isSaving = true; errorMessage = '';
		try { await createStealAttribute(episodeId); await load(); }
		catch (error) { errorMessage = error instanceof Error ? error.message : 'Impossible d’ajouter le vol.'; }
		finally { isSaving = false; }
	}

	async function addPrize() {
		if (!prizeName.trim()) { errorMessage = 'Donnez un nom au lot avant de l’ajouter.'; return; }
		if (!prizeImage) { errorMessage = 'Ajoutez une image pour ce lot.'; return; }
		isSaving = true; errorMessage = '';
		try {
			await createPrizeAttribute(episodeId, { name: prizeName.trim(), description: prizeDescription.trim() || undefined, image: prizeImage });
			prizeName = ''; prizeDescription = ''; prizeImage = null;
			if (prizeImageInput) prizeImageInput.value = '';
			await load();
		} catch (error) { errorMessage = error instanceof Error ? error.message : 'Impossible d’ajouter ce lot.'; }
		finally { isSaving = false; }
	}

	async function remove(attribute: SpecialAttribute) {
		if (!confirm(`Supprimer ${attribute.type === 'steal' ? 'cet attribut Vol' : `le lot « ${attribute.name} »`} ?`)) return;
		isSaving = true; errorMessage = '';
		try { await deleteSpecialAttribute(episodeId, attribute); await load(); }
		catch (error) { errorMessage = error instanceof Error ? error.message : 'Impossible de supprimer cet attribut.'; }
		finally { isSaving = false; }
	}
</script>

<div class="backdrop" role="presentation" onclick={(event) => event.currentTarget === event.target && !isSaving && onclose()}>
	<dialog class="dialog" open aria-labelledby="attributes-title">
		<header><div><p class="eyebrow">Mécaniques de jeu</p><h2 id="attributes-title">Attributs spéciaux</h2></div><button class="close" type="button" aria-label="Fermer" disabled={isSaving} onclick={onclose}>×</button></header>
		<p class="intro">{locked ? 'Les attributs ont été attribués et sont maintenant verrouillés pour préserver la session.' : 'Ajoutez les effets disponibles pour la session. Vous choisirez leurs cases aléatoires après le dispatch des challenges.'}</p>
		{#if !locked}<section class="add-panel" aria-labelledby="steal-title"><div><h3 id="steal-title">Vol</h3><p>Permet de voler un avantage à un autre joueur.</p></div><button type="button" onclick={() => void addSteal()} disabled={isSaving}>Ajouter un vol</button></section>
		<form class="prize-form" onsubmit={(event) => { event.preventDefault(); void addPrize(); }}>
			<div class="prize-heading"><div><h3>Lot</h3><p>Une récompense personnalisée attribuée sur une case.</p></div><span>Récompense</span></div>
			<div class="prize-fields"><label for="prize-name">Nom du lot<input id="prize-name" bind:value={prizeName} disabled={isSaving} placeholder="Ex. Bon cadeau" /></label><label for="prize-description"><span class="field-label">Description <small>(facultatif)</small></span><input id="prize-description" bind:value={prizeDescription} disabled={isSaving} placeholder="Ex. Valeur 20 €" /></label><label class="image-input" for="prize-image">Image du lot<input bind:this={prizeImageInput} id="prize-image" type="file" accept="image/*" disabled={isSaving} onchange={(event) => prizeImage = event.currentTarget.files?.[0] ?? null} />{#if prizeImage}<span>{prizeImage.name}</span>{:else}<span>PNG, JPG ou WebP</span>{/if}</label></div>
			<div class="prize-actions"><button type="submit" disabled={isSaving}>{isSaving ? 'Ajout…' : 'Ajouter le lot'} <span aria-hidden="true">→</span></button></div>
		</form>{/if}
		{#if errorMessage}<p class="error" role="alert">{errorMessage}</p>{/if}
		<section class="list" aria-label="Attributs créés">{#if isLoading}<p class="empty" role="status">Chargement des attributs…</p>{:else if attributes.length}{#each attributes as attribute}<article>{#if attribute.type === 'prize' && attribute.image}<img src={assetUrl(attribute.image)} alt="" />{/if}<div><span class:steal={attribute.type === 'steal'} class="kind">{attribute.type === 'steal' ? 'VOL' : 'LOT'}</span><strong>{attribute.type === 'steal' ? 'Vol' : attribute.name}</strong>{#if attribute.type === 'prize' && attribute.description}<small>{attribute.description}</small>{/if}</div>{#if !locked}<button type="button" onclick={() => void remove(attribute)} disabled={isSaving}>Supprimer</button>{/if}</article>{/each}{:else}<p class="empty">Aucun attribut pour le moment. Ajoutez un vol ou un lot pour préparer leur attribution.</p>{/if}</section>
	</dialog>
</div>

<style>
	.backdrop{position:fixed;z-index:30;inset:0;display:grid;place-items:center;padding:1rem;background:rgba(2,6,23,.72);backdrop-filter:blur(6px)}.dialog{width:min(100%,46rem);max-height:calc(100dvh - 2rem);overflow:auto;border:1px solid #475569;border-radius:1rem;padding:clamp(1.25rem,4vw,2rem);background:#1e293b;color:#f8fafc;box-shadow:0 1.5rem 5rem rgba(0,0,0,.45)}header{display:flex;justify-content:space-between;gap:1rem}.eyebrow{margin:0 0 .45rem;color:#c4b5fd;font-size:.7rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}h2,h3,p{margin:0}h2{font-size:1.55rem;letter-spacing:-.045em}h3{font-size:.93rem}.close{width:2.75rem;min-height:2.75rem;border:1px solid #475569;border-radius:.65rem;background:transparent;color:#cbd5e1;cursor:pointer;font:inherit;font-size:1.6rem}.intro{max-width:42rem;margin:1rem 0 1.25rem;color:#cbd5e1;font-size:.85rem;line-height:1.55}.add-panel{display:grid;grid-template-columns:1fr auto;gap:.75rem;align-items:end;margin-bottom:.75rem;border:1px solid #334155;border-radius:.75rem;padding:1rem;background:#17213a}.add-panel p,.prize-form p{margin-top:.25rem;color:#94a3b8;font-size:.75rem;line-height:1.4}.prize-form{display:grid;gap:1rem;border:1px solid #475569;border-radius:.85rem;padding:1rem;background:linear-gradient(135deg,rgba(124,58,237,.1),#17213a 48%)}.prize-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;border-bottom:1px solid #334155;padding-bottom:.85rem}.prize-heading>span{flex:none;border:1px solid rgba(124,58,237,.45);border-radius:999px;padding:.3rem .5rem;background:rgba(124,58,237,.14);color:#ddd6fe;font-size:.65rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.prize-fields{display:grid;grid-template-columns:1.15fr 1.15fr 1fr;gap:.75rem;align-items:start}.prize-form label{display:grid;gap:.38rem;color:#f8fafc;font-size:.76rem;font-weight:750}.prize-form label span{color:#94a3b8;font-weight:500}.prize-form .field-label{color:#f8fafc;font-weight:750}.prize-form .field-label small{display:inline;margin:0;color:#94a3b8;font-size:inherit;font-weight:500}.prize-form input{width:100%;min-height:2.7rem;border:1px solid #475569;border-radius:.55rem;padding:0 .65rem;background:#0f172a;color:#f8fafc;font:inherit}.prize-form .image-input input{padding:.45rem}.prize-form .image-input>span{min-height:1rem;overflow:hidden;color:#94a3b8;font-size:.67rem;font-weight:600;line-height:1rem;text-overflow:ellipsis;white-space:nowrap}.prize-actions{display:flex;justify-content:flex-end;border-top:1px solid #334155;padding-top:.85rem}.add-panel button,.prize-form button{min-height:2.7rem;border:0;border-radius:.55rem;padding:.55rem .8rem;background:#7c3aed;color:#fff;cursor:pointer;font:inherit;font-size:.78rem;font-weight:800}.prize-form button{min-width:10.5rem}.prize-form button span{margin-left:.8rem}.add-panel button:hover,.prize-form button:hover{background:#8b5cf6}.list{margin-top:1.25rem;border-top:1px solid #334155}.list article{display:flex;align-items:center;justify-content:space-between;gap:1rem;border-bottom:1px solid #334155;padding:.85rem 0}.list article>div{min-width:0}.list img{width:3rem;height:3rem;flex:none;border:1px solid #475569;border-radius:.55rem;object-fit:cover}.kind,strong,small{display:block}.kind{margin-bottom:.3rem;color:#fbbf24;font-size:.65rem;font-weight:850;letter-spacing:.1em}.kind.steal{color:#fda4af}.list strong{font-size:.87rem}.list small{margin-top:.2rem;color:#94a3b8;font-size:.75rem}.list button{min-height:2.5rem;margin-left:auto;border:1px solid rgba(239,68,68,.55);border-radius:.5rem;padding:.45rem .65rem;background:transparent;color:#fca5a5;cursor:pointer;font:inherit;font-size:.75rem;font-weight:750}.empty{padding:1.5rem 0;color:#94a3b8;text-align:center;font-size:.83rem;line-height:1.5}.error{margin:1rem 0;color:#fecaca;font-size:.82rem}.close:focus-visible,.add-panel button:focus-visible,.prize-form button:focus-visible,.prize-form input:focus-visible,.list button:focus-visible{outline:3px solid rgba(167,139,250,.45);outline-offset:3px}.close:disabled,.add-panel button:disabled,.prize-form button:disabled,.prize-form input:disabled,.list button:disabled{cursor:not-allowed;opacity:.6}@media(max-width:620px){.add-panel,.prize-fields{grid-template-columns:1fr}.add-panel button,.prize-form button{width:100%}.prize-actions{justify-content:stretch}.list article{align-items:flex-start}.list article button{width:auto}}@media(max-width:430px){.prize-heading{flex-direction:column}.list article{flex-wrap:wrap}.list article button{width:100%;margin-left:0}}
</style>
