import 'dotenv/config';
import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';
import FormData from 'form-data';
import { CAMUNDA_ENGINE_URL, getCamundaAuth } from './src/camunda';

interface BpmnDeployment {
  name: string;
  file: string;
  deploymentName: string;
  additionalFiles?: { name: string; path: string; contentType: string }[];
}

/**
 * Workflow deployment configurations
 * All BPMN files are located in the bpmn/ directory
 */
const DEPLOYMENTS: BpmnDeployment[] = [
  {
    name: 'Azure OCR Document Processing',
    file: 'bpmn/ocr-demo-workflow.bpmn',
    deploymentName: 'azure-ocr-document-processing',
    additionalFiles: [
      {
        name: 'review-ocr-form.form',
        path: 'forms/review-ocr-form.form',
        contentType: 'application/json'
      }
    ]
  },
  {
    name: 'GitHub AI Agent',
    file: 'bpmn/github-agent-workflow.bpmn',
    deploymentName: 'github-agent-workflow'
  }
];

async function deployWorkflow(deployment: BpmnDeployment): Promise<boolean> {
  const engineUrl = CAMUNDA_ENGINE_URL;
  const camundaAuth = getCamundaAuth();

  const bpmnPath = path.join(process.cwd(), deployment.file);
  if (!fs.existsSync(bpmnPath)) {
    console.warn(`⚠️  BPMN file not found: ${bpmnPath}`);
    console.warn(`   Skipping: ${deployment.name}`);
    return false;
  }

  console.log(`\n📦 Deploying "${deployment.name}"...`);

  const form = new FormData();
  const bpmnFileName = path.basename(deployment.file);
  form.append('deployment-name', `${deployment.deploymentName}-${Date.now()}`);
  form.append('deploy-changed-only', 'false');
  form.append('enable-duplicate-filtering', 'false');
  form.append(bpmnFileName, fs.createReadStream(bpmnPath), {
    contentType: 'text/xml'
  });

  // Add any additional files (forms, etc.)
  if (deployment.additionalFiles) {
    for (const additionalFile of deployment.additionalFiles) {
      const filePath = path.join(process.cwd(), additionalFile.path);
      if (fs.existsSync(filePath)) {
        form.append(additionalFile.name, fs.createReadStream(filePath), {
          contentType: additionalFile.contentType
        });
        console.log(`   + Including: ${additionalFile.name}`);
      }
    }
  }

  try {
    const response = await axios.post(
      `${engineUrl}/deployment/create`,
      form,
      {
        headers: {
          ...form.getHeaders()
        },
        auth: camundaAuth
      }
    );

    const result = response.data;
    if (result && result.deployedProcessDefinitions) {
      const definitions = result.deployedProcessDefinitions;
      const keys = Object.keys(definitions);
      if (keys.length > 0) {
        const proc = definitions[keys[0]];
        console.log(`   ✅ Success`);
        console.log(`      Process Key: ${proc.key}`);
        console.log(`      Definition ID: ${proc.id}`);
        return true;
      }
    }
    
    console.log(`   ✅ Deployed`);
    return true;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error(`   ❌ Failed: ${errorMessage}`);
    if (axios.isAxiosError(error)) {
      console.error(`      Response: ${JSON.stringify(error.response?.data)}`);
    }
    return false;
  }
}

async function deploy(): Promise<void> {
  console.log('');
  console.log('='.repeat(50));
  console.log('Camunda 7 Workflow Deployment');
  console.log('='.repeat(50));
  console.log(`Engine URL: ${CAMUNDA_ENGINE_URL}`);

  let successCount = 0;
  let failCount = 0;

  for (const deployment of DEPLOYMENTS) {
    const success = await deployWorkflow(deployment);
    if (success) {
      successCount++;
    } else {
      failCount++;
    }
  }

  console.log('');
  console.log('='.repeat(50));
  console.log(`Deployment Summary: ${successCount} succeeded, ${failCount} failed`);
  console.log('='.repeat(50));
  
  if (failCount > 0) {
    process.exit(1);
  }
  process.exit(0);
}

deploy();
