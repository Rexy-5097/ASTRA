import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'artifacts', 'benchmark.json');
    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Benchmark metrics file not found.' }, { status: 404 });
    }
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to load benchmark metrics', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
