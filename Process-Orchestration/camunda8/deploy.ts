import 'dotenv/config';
import { Camunda8 } from '@camunda8/sdk';
import * as path from 'path';

const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

async function deploy(): Promise<void> {
  try {
    // Use process.cwd() which works in both development and production
    const bpmnPath = path.join(process.cwd(), 'ocr-demo-workflow.bpmn');
    
    console.log('Deploying BPMN workflow...');
    
    const deployment = await zbc.deployResource({
      processFilename: bpmnPath
    });
    
    console.log('✅ Successfully deployed workflow!');
    // The deployment response structure may vary, so we'll log it safely
    const deploymentAny = deployment as any;
    if (deploymentAny.processes && Array.isArray(deploymentAny.processes) && deploymentAny.processes.length > 0) {
      console.log(`Process ID: ${deploymentAny.processes[0].bpmnProcessId}`);
      console.log(`Version: ${deploymentAny.processes[0].version}`);
    } else {
      console.log('Deployment result:', JSON.stringify(deployment, null, 2));
    }
    
    process.exit(0);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('❌ Deployment failed:', errorMessage);
    if (error instanceof Error && 'details' in error) {
      console.error('Details:', (error as { details: unknown }).details);
    }
    if (error instanceof Error && error.stack) {
      console.error('Stack:', error.stack);
    }
    process.exit(1);
  }
}

deploy();

