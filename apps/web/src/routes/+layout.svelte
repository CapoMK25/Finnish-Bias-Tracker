<script lang="ts">
    // Imports remain the same
    import './layout.css';
    import favicon from '$lib/assets/favicon.svg';
    import { onMount } from 'svelte';
    import { theme } from '$lib/theme.svelte';
    import ThemeToggle from '$lib/components/ThemeToggle.svelte';
    import Banner from '$lib/components/Banner.svelte';

    let { data }: { data?: any } = $props();

    let showBanner = $derived(data?.showBanner ?? false);
   


    onMount(() => theme.init());
</script>


<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<!-- The slot content (children) is only needed in the markup, not the script block -->

<div class="fixed top-3 right-3 z-50">
    <ThemeToggle />
</div>


<!-- Banner Component Integration Here -->
<div class="max-w-[1200px] mx-auto relative z-10 pt-4 pb-6">
    <Banner show={showBanner} /> 
</div >

<!-- The children slot is rendered here. By putting it outside the props block, we resolve the 'children' error. -->
<slot />
