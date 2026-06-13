import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'artifacts', 'calibration.json');
    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Calibration metrics file not found.' }, { status: 404 });
    }
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to load calibration metrics', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
