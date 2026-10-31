<script lang="ts">
        import './layout.css';
        import favicon from '$lib/assets/favicon.svg';
        import { onMount } from 'svelte';
        import { theme } from '$lib/theme.svelte';
        import ThemeToggle from '$lib/components/ThemeToggle.svelte';

        let { children } = $props();

        onMount(() => theme.init());
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="fixed top-3 right-3 z-50">
        <ThemeToggle />
</div>

{@render children()}
