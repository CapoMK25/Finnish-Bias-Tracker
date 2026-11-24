<script lang="ts">
    import { onMount } from 'svelte';

    // ========================================
    // 1. Define the Props Interface
    interface Props {
        show: boolean;
    }

    // 2. Use $props() to extract and initialize the prop
    let { show }: Props = $props(); 
    // ========================================


    let isDismissed: boolean = false;

    $effect(() => {
        if (!show) {
            isDismissed = true; // If not supposed to show, treat it as dismissed.
        } else if (localStorage.getItem('biasTrackerBannerDismissed')) {
            // Check persistent storage first.
            isDismissed = true; 
        } else {
             // Default state: show the banner on first load/first time seeing it.
            isDismissed = false;
        }
    });

    /** Function called when the user clicks 'Ok got it' */
    const handleDismiss = () => {
        localStorage.setItem('biasTrackerBannerDismissed', 'true');
        // Update local state immediately
        isDismissed = true; 
    };
</script>
