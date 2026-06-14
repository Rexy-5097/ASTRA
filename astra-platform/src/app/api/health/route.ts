import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

export const dynamic = 'force-dynamic';

const EXPECTED_DATASET_HASH = 'f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58';
const EXPECTED_MODEL_HASH = 'bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388';

export async function GET() {
  try {
    // 1. Check Dataset File & Fingerprint
    const csvPath = path.join(process.cwd(), 'data', 'scientific_dataset_freeze_v2.csv');
    let datasetHash = '';
    let datasetExists = false;
    let datasetHashMatch = false;

    if (fs.existsSync(csvPath)) {
      datasetExists = true;
      const fileBuffer = fs.readFileSync(csvPath);
      const hashSum = crypto.createHash('sha256');
      hashSum.update(fileBuffer);
      datasetHash = hashSum.digest('hex');
      datasetHashMatch = datasetHash === EXPECTED_DATASET_HASH;
    }

    // 2. Check SQLite Database
    const sqlitePath = path.join(process.cwd(), 'data', 'astra.sqlite');
    const sqliteExists = fs.existsSync(sqlitePath);
    const sqliteSize = sqliteExists ? fs.statSync(sqlitePath).size : -1;

    // 3. Check ONNX Model
    const onnxPath = path.join(process.cwd(), 'data', 'best_star_transformer_shared.onnx');
    const onnxExplainPath = path.join(process.cwd(), 'data', 'best_star_transformer_shared_explain.onnx');
    const onnxExists = fs.existsSync(onnxPath) || fs.existsSync(onnxExplainPath);

    // 4. Calculate System State
    let status: 'READY' | 'DEGRADED' | 'BLOCKED' = 'READY';
    if (!datasetExists || !datasetHashMatch) {
      status = 'BLOCKED';
    } else if (!sqliteExists || !onnxExists) {
      status = 'DEGRADED';
    }

    return NextResponse.json({
      status,
      dataset_hash: datasetHash || 'NOT_FOUND',
      expected_dataset_hash: EXPECTED_DATASET_HASH,
      model_hash: EXPECTED_MODEL_HASH,
      sqlite_loaded: sqliteExists,
      onnx_loaded: onnxExists,
      details: {
        dataset_exists: datasetExists,
        dataset_hash_match: datasetHashMatch,
        sqlite_exists: sqliteExists,
        sqlite_size: sqliteSize,
        onnx_exists: onnxExists,
        onnx_explain_exists: fs.existsSync(onnxExplainPath)
      }
    });
  } catch (error: any) {
    return NextResponse.json({
      status: 'BLOCKED',
      error: error.message || String(error),
      sqlite_loaded: false,
      onnx_loaded: false
    }, { status: 500 });
  }
}
