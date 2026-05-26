import { env } from '../env.js';
import { drizzle } from 'drizzle-orm/postgres-js';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import postgres from 'postgres';
async function main() {
    console.log('Running migrations...');
    // Use a separate connection for migrations (single, no pool)
    const migrationClient = postgres(env.DATABASE_URL, { max: 1 });
    const db = drizzle(migrationClient);
    await migrate(db, { migrationsFolder: './src/db/migrations' });
    console.log('Migrations complete!');
    await migrationClient.end();
    process.exit(0);
}
main().catch((err) => {
    console.error('Migration failed:', err);
    process.exit(1);
});
