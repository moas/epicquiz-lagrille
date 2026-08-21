<script lang="ts">
	import { goto } from '$app/navigation';
	import { saveManagerToken } from '$lib/auth';

	type LoginResponse = {
		token?: string;
		non_field_errors?: string[];
		detail?: string;
	};

	const apiBaseUrl = (import.meta.env.PUBLIC_API_URL ?? '').replace(/\/$/, '');

	let username = $state('');
	let password = $state('');
	let showPassword = $state(false);
	let isSubmitting = $state(false);
	let errorMessage = $state('');
	let successMessage = $state('');

	async function login() {
		errorMessage = '';
		successMessage = '';
		isSubmitting = true;

		try {
			const response = await fetch(`${apiBaseUrl}/api/auth/login/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, password })
			});
			const payload: LoginResponse = await response.json().catch(() => ({}));

			if (!response.ok || !payload.token) {
				throw new Error(payload.non_field_errors?.[0] ?? payload.detail ?? 'Identifiants invalides.');
			}

			saveManagerToken(payload.token);
			await goto('/');
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'La connexion est indisponible.';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<svelte:head>
	<title>Connexion · EpicQuiz - La Grille</title>
	<meta
		name="description"
		content="Connectez-vous à l’espace de gestion La Grille."
	/>
</svelte:head>

<main>
	<section class="brand-panel" aria-label="La Grille">
		<div class="brand-content">
			<div class="brand-lockup">
				<img src="/brand-icon.png" alt="Logo La Grille" class="brand-icon" />
				<span>EpicQuiz - La Grille</span>
			</div>

			<div class="brand-copy">
				<p class="eyebrow">Espace manager</p>
				<h1>Le quiz,<br />orchestré.</h1>
				<p>Créez vos questions, composez vos parties et gardez le jeu sous contrôle.</p>
			</div>
		</div>
		<p class="brand-footer">Une expérience de quiz conçue pour le direct.</p>
	</section>

	<section class="login-panel" aria-labelledby="login-title">
		<div class="login-content">
			<div class="mobile-brand">
				<img src="/brand-icon.png" alt="Logo La Grille" />
				<span>La Grille</span>
			</div>

			<header>
				<p class="section-label">Bon retour</p>
				<h2 id="login-title">Connexion</h2>
				<p class="intro">Utilisez vos identifiants manager pour accéder à votre espace.</p>
			</header>

			<form onsubmit={(event) => { event.preventDefault(); login(); }}>
				<div class="field">
					<label for="username">Nom d’utilisateur</label>
					<input
						id="username"
						name="username"
						type="text"
						autocomplete="username"
						bind:value={username}
						placeholder="ex. clara.dupont"
						required
					/>
				</div>

				<div class="field">
					<div class="label-row">
						<label for="password">Mot de passe</label>
						<a href="mailto:admin@lagrille.local">Besoin d’aide ?</a>
					</div>
					<div class="password-input">
						<input
							id="password"
							name="password"
							type={showPassword ? 'text' : 'password'}
							autocomplete="current-password"
							bind:value={password}
							placeholder="Votre mot de passe"
							required
						/>
						<button
							type="button"
							class="visibility-toggle"
							onclick={() => (showPassword = !showPassword)}
							aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
						>
							{showPassword ? 'Masquer' : 'Afficher'}
						</button>
					</div>
				</div>

				{#if errorMessage}
					<p class="form-message error" role="alert">{errorMessage}</p>
				{/if}
				{#if successMessage}
					<p class="form-message success" role="status">{successMessage}</p>
				{/if}

				<button type="submit" class="submit-button" disabled={isSubmitting}>
					{isSubmitting ? 'Connexion en cours…' : 'Se connecter'}
				</button>
			</form>
		</div>
	</section>
</main>

<style>
	:global(*) {
		box-sizing: border-box;
	}

	:global(html) {
		background: #0f172a;
	}

	:global(body) {
		margin: 0;
		min-width: 320px;
		font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
		color: #f8fafc;
	}

	main {
		display: grid;
		min-height: 100dvh;
		grid-template-columns: minmax(0, 1.08fr) minmax(440px, 0.92fr);
		background: #0f172a;
	}

	.brand-panel {
		position: relative;
		display: flex;
		min-height: 100%;
		flex-direction: column;
		justify-content: space-between;
		overflow: hidden;
		padding: clamp(2rem, 4vw, 4.5rem);
		background:
			radial-gradient(circle at 12% 84%, rgba(56, 189, 248, 0.16), transparent 22rem),
			radial-gradient(circle at 82% 20%, rgba(124, 58, 237, 0.44), transparent 28rem),
			#17213a;
	}

	.brand-panel::after {
		position: absolute;
		right: -11rem;
		bottom: -12rem;
		width: 34rem;
		height: 34rem;
		border: 1px solid rgba(203, 213, 225, 0.13);
		border-radius: 50%;
		box-shadow: 0 0 0 4rem rgba(124, 58, 237, 0.05), 0 0 0 8rem rgba(124, 58, 237, 0.04);
		content: '';
	}

	.brand-content,
	.brand-footer {
		position: relative;
		z-index: 1;
	}

	.brand-lockup,
	.mobile-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 1.125rem;
		font-weight: 750;
		letter-spacing: -0.03em;
	}

	.brand-icon {
		width: 3rem;
		height: 3rem;
		border-radius: 0.9rem;
		background: #f8fafc;
		object-fit: cover;
	}

	.brand-copy {
		max-width: 33rem;
		margin-top: clamp(8rem, 22vh, 15rem);
	}

	.eyebrow,
	.section-label {
		margin: 0 0 1rem;
		color: #c4b5fd;
		font-size: 0.72rem;
		font-weight: 750;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}

	h1,
	h2,
	p {
		margin-top: 0;
	}

	h1 {
		margin-bottom: 1.5rem;
		font-size: clamp(3.3rem, 6vw, 5.75rem);
		line-height: 0.94;
		letter-spacing: -0.07em;
	}

	.brand-copy > p:last-child {
		max-width: 26rem;
		margin-bottom: 0;
		color: #cbd5e1;
		font-size: 1.1rem;
		line-height: 1.65;
	}

	.brand-footer {
		margin: 0;
		color: #94a3b8;
		font-size: 0.875rem;
	}

	.login-panel {
		display: grid;
		place-items: center;
		padding: 2rem;
		background: #0f172a;
	}

	.login-content {
		width: min(100%, 25.5rem);
	}

	.mobile-brand {
		display: none;
		margin-bottom: 4rem;
	}

	.mobile-brand img {
		width: 2.6rem;
		height: 2.6rem;
		border-radius: 0.75rem;
		background: #f8fafc;
		object-fit: cover;
	}

	h2 {
		margin-bottom: 0.7rem;
		font-size: 2.25rem;
		line-height: 1;
		letter-spacing: -0.055em;
	}

	.intro {
		margin-bottom: 2.5rem;
		color: #cbd5e1;
		font-size: 0.96rem;
		line-height: 1.6;
	}

	form {
		display: grid;
		gap: 1.25rem;
	}

	.field {
		display: grid;
		gap: 0.55rem;
	}

	.label-row {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 1rem;
	}

	label {
		color: #f8fafc;
		font-size: 0.875rem;
		font-weight: 650;
	}

	.label-row a {
		color: #a78bfa;
		font-size: 0.78rem;
		text-decoration: none;
	}

	.label-row a:hover {
		color: #c4b5fd;
		text-decoration: underline;
	}

	input {
		width: 100%;
		height: 3.25rem;
		border: 1px solid #475569;
		border-radius: 0.7rem;
		outline: none;
		padding: 0 1rem;
		background: #1e293b;
		color: #f8fafc;
		font: inherit;
		font-size: 0.95rem;
		transition: border-color 150ms ease, box-shadow 150ms ease, background 150ms ease;
	}

	input::placeholder {
		color: #94a3b8;
	}

	input:hover {
		border-color: #64748b;
	}

	input:focus {
		border-color: #a78bfa;
		background: #243247;
		box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.22);
	}

	.password-input {
		position: relative;
	}

	.password-input input {
		padding-right: 5.5rem;
	}

	.visibility-toggle {
		position: absolute;
		top: 50%;
		right: 0.75rem;
		border: 0;
		padding: 0.35rem;
		transform: translateY(-50%);
		background: transparent;
		color: #c4b5fd;
		font: inherit;
		font-size: 0.78rem;
		font-weight: 650;
		cursor: pointer;
	}

	.visibility-toggle:hover {
		color: #ddd6fe;
	}

	.form-message {
		margin: -0.2rem 0 0;
		border-radius: 0.65rem;
		padding: 0.75rem 0.9rem;
		font-size: 0.86rem;
		line-height: 1.4;
	}

	.form-message.error {
		border: 1px solid rgba(239, 68, 68, 0.5);
		background: rgba(127, 29, 29, 0.26);
		color: #fecaca;
	}

	.form-message.success {
		border: 1px solid rgba(34, 197, 94, 0.45);
		background: rgba(20, 83, 45, 0.3);
		color: #bbf7d0;
	}

	.submit-button {
		height: 3.25rem;
		margin-top: 0.35rem;
		border: 1px solid transparent;
		border-radius: 0.7rem;
		background: #7c3aed;
		color: #fff;
		font: inherit;
		font-size: 0.94rem;
		font-weight: 750;
		cursor: pointer;
		transition: transform 120ms ease, background 150ms ease, box-shadow 150ms ease;
	}

	.submit-button:hover:not(:disabled) {
		background: #8b5cf6;
		box-shadow: 0 10px 26px rgba(76, 29, 149, 0.32);
	}

	.submit-button:active:not(:disabled) {
		transform: translateY(1px) scale(0.99);
	}

	.submit-button:focus-visible,
	.visibility-toggle:focus-visible,
	.label-row a:focus-visible {
		outline: 3px solid #a78bfa;
		outline-offset: 3px;
	}

	.submit-button:disabled {
		cursor: wait;
		opacity: 0.72;
	}

	@media (max-width: 820px) {
		main {
			grid-template-columns: 1fr;
		}

		.brand-panel {
			display: none;
		}

		.login-panel {
			align-items: start;
			padding: clamp(1.5rem, 7vw, 3rem);
		}

		.login-content {
			margin-top: clamp(1rem, 10vh, 5rem);
		}

		.mobile-brand {
			display: flex;
		}
	}
</style>
