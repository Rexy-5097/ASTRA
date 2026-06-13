import { NextRequest, NextResponse } from 'next/server';
import { DatabaseSync } from 'node:sqlite';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('q')?.toLowerCase().trim() || '';
    const classFilter = searchParams.get('class') || '';
    const sourceFilter = searchParams.get('source') || '';
    const splitFilter = searchParams.get('split') || '';
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '50');
    
    const dbPath = path.join(process.cwd(), 'data', 'astra.sqlite');
    const db = new DatabaseSync(dbPath);
    
    let sql = 'SELECT * FROM stars WHERE 1=1';
    const params: any[] = [];
    
    if (query) {
      sql += ' AND (CAST(tic_id AS TEXT) LIKE ? OR LOWER(astra_class) LIKE ? OR LOWER(primary_source) LIKE ?)';
      const searchLike = `%${query}%`;
      params.push(searchLike, searchLike, searchLike);
    }
    
    if (classFilter) {
      const classes = classFilter.split(',');
      sql += ` AND astra_class IN (${classes.map(() => '?').join(',')})`;
      params.push(...classes);
    }
    
    if (sourceFilter) {
      const sources = sourceFilter.split(',');
      sql += ` AND period_source IN (${sources.map(() => '?').join(',')})`;
      params.push(...sources);
    }
    
    if (splitFilter && splitFilter !== 'all') {
      sql += ' AND split = ?';
      params.push(splitFilter);
    }
    
    // Get total matching
    const countSql = `SELECT COUNT(*) as count FROM (${sql})`;
    const countStmt = db.prepare(countSql);
    const countResult = countStmt.get(...params) as { count: number };
    const total = countResult.count;
    
    // Add pagination LIMIT & OFFSET
    sql += ' LIMIT ? OFFSET ?';
    params.push(limit, (page - 1) * limit);
    
    const stmt = db.prepare(sql);
    const rows = stmt.all(...params) as any[];
    
    const stars = rows.map((r) => ({
      ...r,
      source_catalogs: r.source_catalogs ? JSON.parse(r.source_catalogs) : [],
      sector_information: r.sector_information ? JSON.parse(r.sector_information) : [],
      has_folded_lc: r.has_folded_lc === 1,
    }));
    
    return NextResponse.json({
      stars,
      total,
      page,
      limit,
      pages: Math.ceil(total / limit),
    });
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to query database', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
