import { scrapeQueue, closeQueue } from '../queue/scrape-queue.js';
async function main() {
    const job = await scrapeQueue.add('test-failure', {
        source_slug: 'totally-fake-source',
        limit: 1,
    }, {
        attempts: 1, // fail fast, no retry
    });
    console.log(`Enqueued job ${job.id} that should fail`);
    await closeQueue();
}
main().catch((err) => {
    console.error(err);
    process.exit(1);
});
