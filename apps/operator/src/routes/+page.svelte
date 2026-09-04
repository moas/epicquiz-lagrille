<script lang="ts">
	import { goto } from '$app/navigation';
	import { clearToken } from '$lib/session';
	function logout() { clearToken(); goto('/login'); }
</script>
<svelte:head><title>Opérateur · La Grille</title></svelte:head>
<main><header><h1>Opérateur</h1><button onclick={logout}>Se déconnecter</button></header><p>La connexion temps réel est maintenue pendant votre session.</p></main>
<style>main{max-width:72rem;margin:0 auto;padding:2rem}header{display:flex;align-items:center;justify-content:space-between;gap:1rem;border-bottom:1px solid #3f3f46;padding-bottom:1rem}h1{margin:0;font-size:1.5rem}p{color:#a1a1aa}button{padding:.55rem .8rem;border:1px solid #52525b;border-radius:.4rem;background:transparent;color:#fafafa;font:inherit;cursor:pointer}</style>
