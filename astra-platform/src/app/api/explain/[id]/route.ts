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
  const { id } = await params;
  const ticId = id.replace('TIC_', '');
  
  // Verify target folder exists
  const targetFolder = path.join(process.cwd(), '..', 'data', 'phase6', 'processed', `TIC_${ticId}`);
  if (!fs.existsSync(targetFolder)) {
    return NextResponse.json({ error: `Target TIC_${ticId} processed folder not found on disk.` }, { status: 404 });
  }
  
  try {
    const pythonPath = path.join(process.cwd(), '..', '.venv', 'bin', 'python');
    const scriptPath = path.join(process.cwd(), '..', 'training', 'explain_inference.py');
    const command = `"${pythonPath}" "${scriptPath}" --input "${targetFolder}"`;
    
    // Run python script and capture stdout
    const { stdout, stderr } = await execPromise(command, {
      cwd: path.join(process.cwd(), '..'),
      maxBuffer: 15 * 1024 * 1024 // 15MB buffer for raw attention floats
    });
    
    if (stderr && stderr.includes('ERROR')) {
      return NextResponse.json({ error: stderr }, { status: 500 });
    }
    
    const report = JSON.parse(stdout.trim());
    return NextResponse.json(report);
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to run explainability inference pipeline', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
