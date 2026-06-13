import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import * as path from 'path';
import { promisify } from 'util';

const execPromise = promisify(exec);

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { tic_id, period, flux } = body;
    
    if (period === undefined || flux === undefined) {
      return NextResponse.json({ error: 'Missing required parameters: period and flux' }, { status: 400 });
    }
    
    const ticIdStr = tic_id ? String(tic_id) : '999999';
    const periodVal = parseFloat(period);
    
    let fluxStr = '';
    if (Array.isArray(flux)) {
      fluxStr = flux.join(',');
    } else {
      fluxStr = String(flux);
    }
    
    if (fluxStr.split(',').length < 50) {
      return NextResponse.json({ error: 'Insufficient observations: minimum 50 values required' }, { status: 400 });
    }
    
    const pythonPath = path.join(process.cwd(), '..', '.venv', 'bin', 'python');
    const scriptPath = path.join(process.cwd(), '..', 'training', 'upload_inference.py');
    
    // Command executes upload_inference.py securely since fluxStr consists of digits and commas
    const command = `"${pythonPath}" "${scriptPath}" --flux "${fluxStr}" --period ${periodVal} --tic_id "${ticIdStr}"`;
    
    const { stdout, stderr } = await execPromise(command, {
      cwd: path.join(process.cwd(), '..'),
      maxBuffer: 15 * 1024 * 1024 // 15MB buffer
    });
    
    if (stderr && stderr.includes('ERROR')) {
      return NextResponse.json({ error: stderr }, { status: 500 });
    }
    
    const report = JSON.parse(stdout.trim());
    return NextResponse.json(report);
  } catch (error: any) {
    return NextResponse.json({ 
      error: 'Failed to run upload inference pipeline', 
      details: error.message || String(error)
    }, { status: 500 });
  }
}
