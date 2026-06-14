import { NextResponse } from 'next/server';
import { DatabaseSync } from 'node:sqlite';
import { pathToFileURL } from 'node:url';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const auditPath = path.join(process.cwd(), 'data', 'artifacts', 'dataset_audit.json');
    const lineagePath = path.join(process.cwd(), 'data', 'artifacts', 'lineage.json');
    
    if (!fs.existsSync(auditPath) || !fs.existsSync(lineagePath)) {
      return NextResponse.json({ error: 'Dataset files not found.' }, { status: 404 });
    }
    
    const audit = JSON.parse(fs.readFileSync(auditPath, 'utf-8'));
    const lineage = JSON.parse(fs.readFileSync(lineagePath, 'utf-8'));
    
    // Compute split class matrix from database
    const dbPath = path.join(process.cwd(), 'data', 'astra.sqlite');
    const db = new DatabaseSync(pathToFileURL(dbPath).toString() + '?immutable=1', { readOnly: true });
    const splitClassCounts = db.prepare('SELECT split, astra_class, COUNT(*) as count FROM stars GROUP BY split, astra_class').all() as any[];
    
    const classSplitMatrix: Record<string, Record<string, number>> = {
      rr_lyrae: { train: 0, val: 0, test: 0 },
      cepheid: { train: 0, val: 0, test: 0 },
      eclipsing_binary: { train: 0, val: 0, test: 0 },
      solar_like: { train: 0, val: 0, test: 0 },
      stable: { train: 0, val: 0, test: 0 }
    };
    
    for (const row of splitClassCounts) {
      if (classSplitMatrix[row.astra_class]) {
        classSplitMatrix[row.astra_class][row.split] = row.count;
      }
    }
    
    return NextResponse.json({
      audit,
      lineage,
      classSplitMatrix
    });
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to load dataset details', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}

