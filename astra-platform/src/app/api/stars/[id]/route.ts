import { NextRequest, NextResponse } from 'next/server';
import { DatabaseSync } from 'node:sqlite';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const ticId = parseInt(id.replace('TIC_', ''));
    
    const dbPath = path.join(process.cwd(), 'data', 'astra.sqlite');
    const db = new DatabaseSync(dbPath);
    
    const stmt = db.prepare('SELECT * FROM stars WHERE tic_id = ?');
    const r = stmt.get(ticId) as any;
    
    if (!r) {
      return NextResponse.json({ error: 'Star not found' }, { status: 404 });
    }
    
    const star = {
      ...r,
      source_catalogs: r.source_catalogs ? JSON.parse(r.source_catalogs) : [],
      sector_information: r.sector_information ? JSON.parse(r.sector_information) : [],
      has_folded_lc: r.has_folded_lc === 1,
    };
    
    return NextResponse.json(star);
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to query database', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
