import { NextRequest, NextResponse } from 'next/server';
import { DatabaseSync } from 'node:sqlite';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('q')?.toLowerCase().trim() || '';
    
    if (!query || query.length < 2) {
      return NextResponse.json({ results: [] });
    }
    
    const dbPath = path.join(process.cwd(), 'data', 'astra.sqlite');
    const db = new DatabaseSync(dbPath);
    
    // Fuzzy matching using SQLite parameters
    const stmt = db.prepare(`
      SELECT tic_id, astra_class, ra, dec, period, period_source, n_sectors 
      FROM stars 
      WHERE CAST(tic_id AS TEXT) LIKE ? 
         OR LOWER(astra_class) LIKE ? 
         OR LOWER(primary_source) LIKE ? 
         OR LOWER(catalog_label) LIKE ?
      LIMIT 20
    `);
    
    const searchLike = `%${query}%`;
    const rows = stmt.all(searchLike, searchLike, searchLike, searchLike) as any[];
    
    const results = rows.map((r) => ({
      tic_id: r.tic_id,
      astra_class: r.astra_class,
      ra: r.ra,
      dec: r.dec,
      period: r.period,
      period_source: r.period_source,
      n_sectors: r.n_sectors,
    }));
    
    return NextResponse.json({ results });
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to search database', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
