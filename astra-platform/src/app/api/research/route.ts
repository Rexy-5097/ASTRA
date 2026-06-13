import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const findingsPath = path.join(process.cwd(), 'data', 'artifacts', 'research_findings.json');
    const uncertaintyPath = path.join(process.cwd(), 'data', 'artifacts', 'uncertainty.json');
    
    if (!fs.existsSync(findingsPath) || !fs.existsSync(uncertaintyPath)) {
      return NextResponse.json({ error: 'Research files not found.' }, { status: 404 });
    }
    
    const findings = JSON.parse(fs.readFileSync(findingsPath, 'utf-8'));
    const uncertainty = JSON.parse(fs.readFileSync(uncertaintyPath, 'utf-8'));
    
    return NextResponse.json({
      findings,
      uncertainty
    });
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to load research findings', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}

