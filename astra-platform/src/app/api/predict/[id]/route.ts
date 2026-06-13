import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { promisify } from 'util';

const execPromise = promisify(exec);

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const ticId = id.replace('TIC_', '');
    
    // Check if target folder exists
    const targetFolder = path.join(process.cwd(), '..', 'data', 'phase6', 'processed', `TIC_${ticId}`);
    if (!fs.existsSync(targetFolder)) {
      return NextResponse.json({ error: `Target folder for TIC_${ticId} not found.` }, { status: 404 });
    }
    
    const pythonPath = path.join(process.cwd(), '..', '.venv', 'bin', 'python');
    const scriptPath = path.join(process.cwd(), '..', 'training', 'predict_inference.py');
    const command = `"${pythonPath}" "${scriptPath}" --input "${targetFolder}"`;
    
    // Run PyTorch MC Dropout script and capture output JSON
    const { stdout, stderr } = await execPromise(command, {
      cwd: path.join(process.cwd(), '..'),
      maxBuffer: 5 * 1024 * 1024
    });
    
    if (stderr && stderr.includes('ERROR')) {
      return NextResponse.json({ error: stderr }, { status: 500 });
    }
    
    const result = JSON.parse(stdout.trim());
    return NextResponse.json(result);
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to run PyTorch predictive uncertainty inference', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
