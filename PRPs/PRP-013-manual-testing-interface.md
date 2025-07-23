# PRP-013: Manual Testing Interface - Comprehensive System Testing Dashboard

**Stable ID**: PRP-013 | **Priority**: P0 | **Status**: new  
**Created**: 2025-07-23 | **Dependencies**: All PRPs (000-012)  
**Blocking**: None (Final PRP)

## Executive Summary

PRP-013 implements a comprehensive manual testing interface that provides end-to-end system validation, lead management, and business metrics visualization for the LeadShop MVP. The interface enables administrators and QA teams to test the complete pipeline, monitor system performance, and validate business logic through an intuitive web-based dashboard.

**Business Impact**: Ensures system reliability and quality before production deployment while providing ongoing monitoring and validation capabilities for operational excellence.

## Business Logic & Core Requirements

### Primary Objectives
- Provide comprehensive testing interface for the entire LeadShop pipeline
- Enable bulk lead processing and batch testing capabilities
- Visualize business metrics and system performance in real-time
- Support manual validation of automated processes
- Facilitate QA workflows and regression testing

### Integration Points
- **Complete Pipeline Testing**: Integration with all PRPs (000-012)
- **Lead Management**: Bulk import/export with validation and deduplication
- **Real-time Monitoring**: Live system status and performance metrics
- **Business Analytics**: Revenue attribution and impact visualization
- **Quality Assurance**: Manual validation and testing workflows

### Success Metrics
- 100% pipeline component test coverage
- <2 second dashboard load time with real-time updates
- Support for 1000+ lead batch processing
- 99.5% test execution success rate
- Comprehensive audit trail for all testing activities

## Technical Architecture

### Core Components

#### 1. Main Testing Dashboard
```typescript
// components/TestingDashboard.tsx
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useWebSocket } from '@/hooks/useWebSocket';
import { TestingMetrics } from '@/components/TestingMetrics';
import { LeadManager } from '@/components/LeadManager';
import { PipelineStatus } from '@/components/PipelineStatus';

interface TestingDashboardProps {
  user: User;
  permissions: Permission[];
}

interface SystemStatus {
  pipeline_health: 'healthy' | 'degraded' | 'down';
  active_tests: number;
  completed_tests: number;
  failed_tests: number;
  system_metrics: {
    cpu_usage: number;
    memory_usage: number;
    database_connections: number;
    queue_depth: number;
  };
}

export const TestingDashboard: React.FC<TestingDashboardProps> = ({ user, permissions }) => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [activeTests, setActiveTests] = useState<TestExecution[]>([]);
  const [testHistory, setTestHistory] = useState<TestResult[]>([]);
  const [loading, setLoading] = useState(true);

  // WebSocket connection for real-time updates
  const socket = useWebSocket('/api/v1/testing/ws', {
    onMessage: (data) => {
      switch (data.type) {
        case 'system_status':
          setSystemStatus(data.payload);
          break;
        case 'test_update':
          setActiveTests(prev => updateTestInList(prev, data.payload));
          break;
        case 'test_completed':
          setTestHistory(prev => [data.payload, ...prev.slice(0, 99)]);
          setActiveTests(prev => prev.filter(test => test.id !== data.payload.id));
          break;
      }
    },
    reconnectAttempts: 5,
    reconnectInterval: 3000
  });

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [statusResponse, testsResponse, historyResponse] = await Promise.all([
        fetch('/api/v1/testing/status'),
        fetch('/api/v1/testing/active'),
        fetch('/api/v1/testing/history?limit=50')
      ]);

      setSystemStatus(await statusResponse.json());
      setActiveTests(await testsResponse.json());
      setTestHistory(await historyResponse.json());
    } catch (error) {
      console.error('Failed to load initial data:', error);
    } finally {
      setLoading(false);
    }
  };

  const runPipelineTest = async (leadData: Partial<Lead>) => {
    try {
      const response = await fetch('/api/v1/testing/run-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_data: leadData, test_type: 'full_pipeline' })
      });

      if (!response.ok) {
        throw new Error('Failed to start pipeline test');
      }

      const testExecution = await response.json();
      setActiveTests(prev => [...prev, testExecution]);
      
      return testExecution;
    } catch (error) {
      console.error('Pipeline test failed:', error);
      throw error;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading testing dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">LeadShop Testing Interface</h1>
              <p className="mt-1 text-sm text-gray-500">
                Comprehensive system testing and validation dashboard
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <SystemHealthIndicator status={systemStatus?.pipeline_health || 'down'} />
              <Button 
                onClick={() => runPipelineTest({})} 
                className="bg-blue-600 hover:bg-blue-700"
                disabled={systemStatus?.pipeline_health !== 'healthy'}
              >
                Run Full Pipeline Test
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* System Status Panel */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                  System Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                <PipelineStatus systemStatus={systemStatus} />
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button 
                  variant="outline" 
                  className="w-full justify-start"
                  onClick={() => runPipelineTest({ website_url: 'https://example.com' })}
                >
                  Test Sample Lead
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full justify-start"
                  onClick={() => window.open('/api/v1/testing/metrics', '_blank')}
                >
                  View System Metrics
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full justify-start"
                  onClick={() => downloadTestReport()}
                >
                  Download Test Report
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Main Testing Area */}
          <div className="lg:col-span-2">
            <div className="space-y-6">
              {/* Active Tests */}
              <Card>
                <CardHeader>
                  <CardTitle>Active Tests ({activeTests.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  {activeTests.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No active tests running</p>
                  ) : (
                    <div className="space-y-4">
                      {activeTests.map(test => (
                        <TestExecutionCard key={test.id} test={test} />
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Testing Metrics */}
              <TestingMetrics testHistory={testHistory} systemStatus={systemStatus} />

              {/* Lead Manager */}
              <LeadManager onTestLead={runPipelineTest} permissions={permissions} />
            </div>
          </div>
        </div>

        {/* Test History */}
        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>Recent Test History</CardTitle>
            </CardHeader>
            <CardContent>
              <TestHistoryTable testHistory={testHistory} />
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

const SystemHealthIndicator: React.FC<{ status: string }> = ({ status }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500';
      case 'degraded': return 'bg-yellow-500';
      case 'down': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="flex items-center">
      <div className={`w-3 h-3 rounded-full ${getStatusColor(status)} mr-2`}></div>
      <span className="text-sm font-medium capitalize">{status}</span>
    </div>
  );
};
```

#### 2. Lead Management System
```typescript
// components/LeadManager.tsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import Papa from 'papaparse';

interface LeadManagerProps {
  onTestLead: (leadData: Partial<Lead>) => Promise<any>;
  permissions: Permission[];
}

interface ImportProgress {
  total: number;
  processed: number;
  successful: number;
  failed: number;
  errors: ImportError[];
}

interface ImportError {
  row: number;
  field: string;
  message: string;
  data: any;
}

export const LeadManager: React.FC<LeadManagerProps> = ({ onTestLead, permissions }) => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLeads, setSelectedLeads] = useState<Set<number>>(new Set());
  const [importProgress, setImportProgress] = useState<ImportProgress | null>(null);
  const [isImporting, setIsImporting] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      processCSVFile(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    maxFiles: 1
  });

  const processCSVFile = async (file: File) => {
    setIsImporting(true);
    setImportProgress({ total: 0, processed: 0, successful: 0, failed: 0, errors: [] });

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: async (results) => {
        const data = results.data as any[];
        setImportProgress(prev => ({ ...prev!, total: data.length }));

        const processedLeads: Lead[] = [];
        const errors: ImportError[] = [];

        for (let i = 0; i < data.length; i++) {
          const row = data[i];
          
          try {
            // Validate required fields
            const leadData = await validateAndTransformLead(row, i + 2); // +2 for header and 0-index
            
            // Create lead in database
            const response = await fetch('/api/v1/leads', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(leadData)
            });

            if (response.ok) {
              const createdLead = await response.json();
              processedLeads.push(createdLead);
              setImportProgress(prev => ({
                ...prev!,
                processed: prev!.processed + 1,
                successful: prev!.successful + 1
              }));
            } else {
              const error = await response.json();
              errors.push({
                row: i + 2,
                field: 'general',
                message: error.message || 'Failed to create lead',
                data: row
              });
              setImportProgress(prev => ({
                ...prev!,
                processed: prev!.processed + 1,
                failed: prev!.failed + 1,
                errors: [...prev!.errors, ...errors]
              }));
            }
          } catch (error) {
            errors.push({
              row: i + 2,
              field: 'validation',
              message: error instanceof Error ? error.message : 'Unknown validation error',
              data: row
            });
            setImportProgress(prev => ({
              ...prev!,
              processed: prev!.processed + 1,
              failed: prev!.failed + 1,
              errors: [...prev!.errors, ...errors]
            }));
          }

          // Small delay to prevent overwhelming the API
          await new Promise(resolve => setTimeout(resolve, 100));
        }

        setLeads(prev => [...prev, ...processedLeads]);
        setIsImporting(false);
      },
      error: (error) => {
        console.error('CSV parsing error:', error);
        setIsImporting(false);
      }
    });
  };

  const validateAndTransformLead = async (row: any, rowNumber: number): Promise<Partial<Lead>> => {
    const errors: string[] = [];

    // Required field validation
    if (!row.business_name || row.business_name.trim() === '') {
      errors.push('Business name is required');
    }
    if (!row.website_url || row.website_url.trim() === '') {
      errors.push('Website URL is required');
    }
    if (!row.email || row.email.trim() === '') {
      errors.push('Email is required');
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (row.email && !emailRegex.test(row.email)) {
      errors.push('Invalid email format');
    }

    // URL validation
    if (row.website_url) {
      try {
        new URL(row.website_url.startsWith('http') ? row.website_url : `https://${row.website_url}`);
      } catch {
        errors.push('Invalid website URL format');
      }
    }

    if (errors.length > 0) {
      throw new Error(`Row ${rowNumber}: ${errors.join(', ')}`);
    }

    return {
      business_name: row.business_name.trim(),
      website_url: row.website_url.startsWith('http') ? row.website_url : `https://${row.website_url}`,
      email: row.email.trim().toLowerCase(),
      contact_name: row.contact_name?.trim() || null,
      phone: row.phone?.trim() || null,
      industry: row.industry?.trim() || null,
      naics_code: row.naics_code?.trim() || null,
      location: row.location?.trim() || null,
      annual_revenue: row.annual_revenue ? parseFloat(row.annual_revenue) : null,
      employee_count: row.employee_count ? parseInt(row.employee_count) : null,
      notes: row.notes?.trim() || null
    };
  };

  const runBatchTests = async () => {
    const selectedLeadArray = leads.filter(lead => selectedLeads.has(lead.id));
    
    for (const lead of selectedLeadArray) {
      try {
        await onTestLead(lead);
        await new Promise(resolve => setTimeout(resolve, 2000)); // Rate limiting
      } catch (error) {
        console.error(`Failed to test lead ${lead.id}:`, error);
      }
    }
    
    setSelectedLeads(new Set());
  };

  const exportLeads = () => {
    const csvData = leads.map(lead => ({
      id: lead.id,
      business_name: lead.business_name,
      website_url: lead.website_url,
      email: lead.email,
      contact_name: lead.contact_name,
      phone: lead.phone,
      industry: lead.industry,
      status: lead.status,
      created_at: lead.created_at
    }));

    const csv = Papa.unparse(csvData);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `leads_export_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lead Management</CardTitle>
      </CardHeader>
      <CardContent>
        {/* File Upload Area */}
        <div {...getRootProps()} className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
        `}>
          <input {...getInputProps()} />
          <div className="mx-auto w-12 h-12 text-gray-400 mb-4">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          {isDragActive ? (
            <p className="text-blue-600">Drop the CSV file here...</p>
          ) : (
            <div>
              <p className="text-gray-600 mb-2">Drag & drop a CSV file here, or click to select</p>
              <p className="text-sm text-gray-500">Supports CSV, XLS, and XLSX files</p>
            </div>
          )}
        </div>

        {/* Import Progress */}
        {isImporting && importProgress && (
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium">Importing leads...</span>
              <span className="text-sm text-gray-600">
                {importProgress.processed} / {importProgress.total}
              </span>
            </div>
            <Progress 
              value={(importProgress.processed / importProgress.total) * 100} 
              className="mb-2"
            />
            <div className="flex justify-between text-sm text-gray-600">
              <span>✅ Successful: {importProgress.successful}</span>
              <span>❌ Failed: {importProgress.failed}</span>
            </div>
          </div>
        )}

        {/* Import Errors */}
        {importProgress?.errors && importProgress.errors.length > 0 && (
          <div className="mt-4 p-4 bg-red-50 rounded-lg">
            <h4 className="text-sm font-medium text-red-800 mb-2">Import Errors:</h4>
            <div className="max-h-32 overflow-y-auto">
              {importProgress.errors.slice(0, 10).map((error, index) => (
                <div key={index} className="text-sm text-red-700 mb-1">
                  Row {error.row}: {error.message}
                </div>
              ))}
              {importProgress.errors.length > 10 && (
                <div className="text-sm text-red-600">
                  ... and {importProgress.errors.length - 10} more errors
                </div>
              )}
            </div>
          </div>
        )}

        {/* Lead Actions */}
        {leads.length > 0 && (
          <div className="mt-6 flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                {selectedLeads.size} of {leads.length} leads selected
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelectedLeads(new Set(leads.map(l => l.id)))}
              >
                Select All
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelectedLeads(new Set())}
              >
                Clear Selection
              </Button>
            </div>
            <div className="flex space-x-2">
              <Button
                size="sm"
                variant="outline"
                onClick={exportLeads}
              >
                Export CSV
              </Button>
              <Button
                size="sm"
                onClick={runBatchTests}
                disabled={selectedLeads.size === 0}
                className="bg-blue-600 hover:bg-blue-700"
              >
                Test Selected ({selectedLeads.size})
              </Button>
            </div>
          </div>
        )}

        {/* Lead Table */}
        {leads.length > 0 && (
          <div className="mt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <input
                      type="checkbox"
                      checked={selectedLeads.size === leads.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedLeads(new Set(leads.map(l => l.id)));
                        } else {
                          setSelectedLeads(new Set());
                        }
                      }}
                    />
                  </TableHead>
                  <TableHead>Business Name</TableHead>
                  <TableHead>Website</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.map((lead) => (
                  <TableRow key={lead.id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={selectedLeads.has(lead.id)}
                        onChange={(e) => {
                          const newSelected = new Set(selectedLeads);
                          if (e.target.checked) {
                            newSelected.add(lead.id);
                          } else {
                            newSelected.delete(lead.id);
                          }
                          setSelectedLeads(newSelected);
                        }}
                      />
                    </TableCell>
                    <TableCell className="font-medium">{lead.business_name}</TableCell>
                    <TableCell>
                      <a 
                        href={lead.website_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {lead.website_url}
                      </a>
                    </TableCell>
                    <TableCell>{lead.email}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        lead.status === 'completed' ? 'bg-green-100 text-green-800' :
                        lead.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                        lead.status === 'failed' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {lead.status}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onTestLead(lead)}
                      >
                        Test
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
```

#### 3. Testing Metrics Visualization
```typescript
// components/TestingMetrics.tsx
import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';

interface TestingMetricsProps {
  testHistory: TestResult[];
  systemStatus: SystemStatus | null;
}

interface MetricsSummary {
  totalTests: number;
  successRate: number;
  averageExecutionTime: number;
  averageSpamScore: number;
  pipelineStepSuccess: Record<string, number>;
  performanceMetrics: {
    timestamp: string;
    cpu_usage: number;
    memory_usage: number;
    response_time: number;
  }[];
}

export const TestingMetrics: React.FC<TestingMetricsProps> = ({ testHistory, systemStatus }) => {
  const metrics = useMemo(() => {
    if (!testHistory.length) return null;

    const summary: MetricsSummary = {
      totalTests: testHistory.length,
      successRate: (testHistory.filter(t => t.status === 'success').length / testHistory.length) * 100,
      averageExecutionTime: testHistory.reduce((acc, t) => acc + (t.execution_time || 0), 0) / testHistory.length,
      averageSpamScore: testHistory.reduce((acc, t) => acc + (t.spam_score || 0), 0) / testHistory.length,
      pipelineStepSuccess: {},
      performanceMetrics: []
    };

    // Calculate pipeline step success rates
    const stepCounts: Record<string, { success: number; total: number }> = {};
    testHistory.forEach(test => {
      test.pipeline_results?.forEach((step: any) => {
        if (!stepCounts[step.step_name]) {
          stepCounts[step.step_name] = { success: 0, total: 0 };
        }
        stepCounts[step.step_name].total++;
        if (step.status === 'success') {
          stepCounts[step.step_name].success++;
        }
      });
    });

    Object.entries(stepCounts).forEach(([step, counts]) => {
      summary.pipelineStepSuccess[step] = (counts.success / counts.total) * 100;
    });

    // Generate performance metrics (last 24 hours)
    const last24Hours = Date.now() - (24 * 60 * 60 * 1000);
    const recentTests = testHistory.filter(t => new Date(t.created_at).getTime() > last24Hours);
    
    // Group by hour
    const hourlyMetrics: Record<string, { tests: number; avgTime: number; successRate: number }> = {};
    recentTests.forEach(test => {
      const hour = new Date(test.created_at).toISOString().slice(0, 13) + ':00:00.000Z';
      if (!hourlyMetrics[hour]) {
        hourlyMetrics[hour] = { tests: 0, avgTime: 0, successRate: 0 };
      }
      hourlyMetrics[hour].tests++;
      hourlyMetrics[hour].avgTime += test.execution_time || 0;
      if (test.status === 'success') {
        hourlyMetrics[hour].successRate++;
      }
    });

    summary.performanceMetrics = Object.entries(hourlyMetrics).map(([timestamp, data]) => ({
      timestamp,
      cpu_usage: systemStatus?.system_metrics.cpu_usage || 0,
      memory_usage: systemStatus?.system_metrics.memory_usage || 0,
      response_time: data.avgTime / data.tests || 0
    }));

    return summary;
  }, [testHistory, systemStatus]);

  if (!metrics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Testing Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500 text-center py-8">No test data available</p>
        </CardContent>
      </Card>
    );
  }

  const pipelineStepData = Object.entries(metrics.pipelineStepSuccess).map(([step, successRate]) => ({
    step: step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    successRate: Math.round(successRate),
    failureRate: Math.round(100 - successRate)
  }));

  const statusDistribution = [
    { name: 'Success', value: testHistory.filter(t => t.status === 'success').length, color: '#10B981' },
    { name: 'Failed', value: testHistory.filter(t => t.status === 'failed').length, color: '#EF4444' },
    { name: 'Pending', value: testHistory.filter(t => t.status === 'pending').length, color: '#F59E0B' }
  ];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Tests</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.totalTests}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Success Rate</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.successRate.toFixed(1)}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Avg Execution Time</p>
                <p className="text-2xl font-bold text-gray-900">{(metrics.averageExecutionTime / 1000).toFixed(1)}s</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Avg Spam Score</p>
                <p className="text-2xl font-bold text-gray-900">{metrics.averageSpamScore.toFixed(1)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline Step Success Rates */}
        <Card>
          <CardHeader>
            <CardTitle>Pipeline Step Success Rates</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={pipelineStepData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="step" 
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="successRate" fill="#10B981" name="Success Rate %" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Test Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Test Status Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statusDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Performance Trends */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>System Performance (Last 24 Hours)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={metrics.performanceMetrics}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                />
                <Line 
                  type="monotone" 
                  dataKey="response_time" 
                  stroke="#8884d8" 
                  name="Response Time (ms)"
                />
                <Line 
                  type="monotone" 
                  dataKey="cpu_usage" 
                  stroke="#82ca9d" 
                  name="CPU Usage %"
                />
                <Line 
                  type="monotone" 
                  dataKey="memory_usage" 
                  stroke="#ffc658" 
                  name="Memory Usage %"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
```

#### 4. Pipeline Status Monitor
```typescript
// components/PipelineStatus.tsx
import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

interface PipelineStatusProps {
  systemStatus: SystemStatus | null;
}

interface PipelineStep {
  name: string;
  status: 'healthy' | 'warning' | 'error' | 'unknown';
  lastCheck: string;
  metrics?: {
    responseTime?: number;
    successRate?: number;
    errorCount?: number;
  };
}

export const PipelineStatus: React.FC<PipelineStatusProps> = ({ systemStatus }) => {
  const pipelineSteps: PipelineStep[] = [
    {
      name: 'S3 Storage',
      status: 'healthy',
      lastCheck: '2 minutes ago',
      metrics: { responseTime: 45, successRate: 99.9 }
    },
    {
      name: 'Lead Data Model',
      status: 'healthy',
      lastCheck: '1 minute ago',
      metrics: { responseTime: 12, successRate: 100 }
    },
    {
      name: 'Assessment Orchestrator',
      status: 'healthy',
      lastCheck: '30 seconds ago',
      metrics: { responseTime: 156, successRate: 98.5 }
    },
    {
      name: 'PageSpeed Integration',
      status: 'warning',
      lastCheck: '45 seconds ago',
      metrics: { responseTime: 2300, successRate: 95.2, errorCount: 3 }
    },
    {
      name: 'Security Scraper',
      status: 'healthy',
      lastCheck: '1 minute ago',
      metrics: { responseTime: 890, successRate: 97.8 }
    },
    {
      name: 'GBP Integration',
      status: 'healthy',
      lastCheck: '2 minutes ago',
      metrics: { responseTime: 1200, successRate: 94.5 }
    },
    {
      name: 'SEMrush Integration',
      status: 'healthy',
      lastCheck: '1 minute ago',
      metrics: { responseTime: 1800, successRate: 96.7 }
    },
    {
      name: 'LLM Visual Analysis',
      status: 'healthy',
      lastCheck: '30 seconds ago',
      metrics: { responseTime: 3400, successRate: 98.9 }
    },
    {
      name: 'Score Calculator',
      status: 'healthy',
      lastCheck: '15 seconds ago',
      metrics: { responseTime: 89, successRate: 100 }
    },
    {
      name: 'Content Generator',
      status: 'healthy',
      lastCheck: '1 minute ago',
      metrics: { responseTime: 2100, successRate: 97.3 }
    },
    {
      name: 'Report Builder',
      status: 'healthy',
      lastCheck: '45 seconds ago',
      metrics: { responseTime: 4500, successRate: 99.1 }
    },
    {
      name: 'Email Formatter',
      status: 'healthy',
      lastCheck: '30 seconds ago',
      metrics: { responseTime: 340, successRate: 99.8 }
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500';
      case 'warning': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-4">
      {/* System Metrics */}
      {systemStatus && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-600 mb-1">CPU Usage</p>
            <Progress value={systemStatus.system_metrics.cpu_usage} className="mb-1" />
            <p className="text-xs text-gray-500">{systemStatus.system_metrics.cpu_usage}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">Memory Usage</p>
            <Progress value={systemStatus.system_metrics.memory_usage} className="mb-1" />
            <p className="text-xs text-gray-500">{systemStatus.system_metrics.memory_usage}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">DB Connections</p>
            <p className="text-lg font-semibold">{systemStatus.system_metrics.database_connections}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">Queue Depth</p>
            <p className="text-lg font-semibold">{systemStatus.system_metrics.queue_depth}</p>
          </div>
        </div>
      )}

      {/* Pipeline Steps */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-900">Pipeline Components</h4>
        {pipelineSteps.map((step, index) => (
          <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full ${getStatusColor(step.status)} mr-3`}></div>
              <div>
                <p className="text-sm font-medium text-gray-900">{step.name}</p>
                <p className="text-xs text-gray-500">Last check: {step.lastCheck}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {step.metrics?.responseTime && (
                <div className="text-right">
                  <p className="text-xs text-gray-600">Response</p>
                  <p className="text-sm font-medium">{step.metrics.responseTime}ms</p>
                </div>
              )}
              {step.metrics?.successRate && (
                <div className="text-right">
                  <p className="text-xs text-gray-600">Success</p>
                  <p className="text-sm font-medium">{step.metrics.successRate}%</p>
                </div>
              )}
              <Badge className={getStatusBadgeColor(step.status)}>
                {step.status}
              </Badge>
            </div>
          </div>
        ))}
      </div>

      {/* Active Tests Counter */}
      {systemStatus && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-sm font-medium text-blue-900">Active Tests</p>
              <p className="text-2xl font-bold text-blue-900">{systemStatus.active_tests}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-blue-700">Completed Today</p>
              <p className="text-lg font-semibold text-blue-900">{systemStatus.completed_tests}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
```

## API Endpoints

### Testing API
```python
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, List, Any, Optional
import asyncio
import json
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/testing", tags=["testing"])

@router.get("/status")
async def get_system_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current system status and health metrics."""
    try:
        # Check pipeline health
        pipeline_health = await check_pipeline_health()
        
        # Get system metrics
        system_metrics = await get_system_metrics()
        
        # Get active test count
        active_tests = await count_active_tests()
        completed_tests = await count_completed_tests_today()
        failed_tests = await count_failed_tests_today()
        
        return {
            "pipeline_health": pipeline_health,
            "active_tests": active_tests,
            "completed_tests": completed_tests,
            "failed_tests": failed_tests,
            "system_metrics": system_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")

@router.post("/run-pipeline")
async def run_pipeline_test(
    test_request: PipelineTestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Run a complete pipeline test for a lead."""
    try:
        # Validate lead data
        if not test_request.lead_data.get('website_url'):
            raise HTTPException(status_code=400, detail="Website URL is required")
        
        # Create test execution record
        test_execution = TestExecution(
            id=str(uuid4()),
            user_id=current_user.id,
            test_type=test_request.test_type,
            lead_data=test_request.lead_data,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        await database.store_test_execution(test_execution)
        
        # Start pipeline test in background
        background_tasks.add_task(execute_pipeline_test, test_execution.id)
        
        return {
            "test_id": test_execution.id,
            "status": "started",
            "estimated_duration": "5-8 minutes",
            "created_at": test_execution.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start pipeline test: {e}")
        raise HTTPException(status_code=500, detail="Failed to start pipeline test")

async def execute_pipeline_test(test_id: str):
    """Execute complete pipeline test with progress tracking."""
    try:
        test_execution = await database.get_test_execution(test_id)
        if not test_execution:
            logger.error(f"Test execution {test_id} not found")
            return
        
        # Update status to running
        test_execution.status = 'running'
        test_execution.started_at = datetime.utcnow()
        await database.update_test_execution(test_execution)
        
        # Broadcast status update
        await websocket_manager.broadcast_to_user(
            test_execution.user_id,
            {
                "type": "test_update",
                "payload": test_execution.to_dict()
            }
        )
        
        pipeline_results = []
        total_steps = 12
        current_step = 0
        
        # Step 1: S3 Setup Test
        current_step += 1
        step_result = await test_s3_integration(test_execution.lead_data)
        pipeline_results.append({
            "step_name": "s3_setup",
            "step_number": current_step,
            "status": step_result["status"],
            "duration": step_result["duration"],
            "details": step_result["details"],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        if step_result["status"] != "success":
            await fail_test_execution(test_execution, "S3 integration failed", pipeline_results)
            return
        
        # Step 2: Lead Data Model Test
        current_step += 1
        step_result = await test_lead_data_model(test_execution.lead_data)
        pipeline_results.append({
            "step_name": "lead_data_model",
            "step_number": current_step,
            "status": step_result["status"],
            "duration": step_result["duration"],
            "details": step_result["details"],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        if step_result["status"] != "success":
            await fail_test_execution(test_execution, "Lead data model failed", pipeline_results)
            return
        
        # Continue with remaining steps...
        # Step 3: Assessment Orchestrator
        current_step += 1
        step_result = await test_assessment_orchestrator(test_execution.lead_data)
        pipeline_results.append(create_step_result("assessment_orchestrator", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 4: PageSpeed Integration
        current_step += 1
        step_result = await test_pagespeed_integration(test_execution.lead_data["website_url"])
        pipeline_results.append(create_step_result("pagespeed_integration", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 5: Security Scraper
        current_step += 1
        step_result = await test_security_scraper(test_execution.lead_data["website_url"])
        pipeline_results.append(create_step_result("security_scraper", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 6: GBP Integration
        current_step += 1
        step_result = await test_gbp_integration(test_execution.lead_data)
        pipeline_results.append(create_step_result("gbp_integration", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 7: ScreenshotOne Integration
        current_step += 1
        step_result = await test_screenshot_integration(test_execution.lead_data["website_url"])
        pipeline_results.append(create_step_result("screenshot_integration", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 8: SEMrush Integration
        current_step += 1
        step_result = await test_semrush_integration(test_execution.lead_data["website_url"])
        pipeline_results.append(create_step_result("semrush_integration", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 9: LLM Visual Analysis
        current_step += 1
        step_result = await test_llm_visual_analysis(test_execution.lead_data["website_url"])
        pipeline_results.append(create_step_result("llm_visual_analysis", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 10: Score Calculator
        current_step += 1
        step_result = await test_score_calculator(test_execution.lead_data)
        pipeline_results.append(create_step_result("score_calculator", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 11: LLM Content Generator
        current_step += 1
        step_result = await test_content_generator(test_execution.lead_data)
        pipeline_results.append(create_step_result("content_generator", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Step 12: Report Builder & Email Formatter
        current_step += 1
        step_result = await test_report_and_email(test_execution.lead_data)
        pipeline_results.append(create_step_result("report_and_email", current_step, step_result))
        await update_test_progress(test_execution, current_step, total_steps, pipeline_results)
        
        # Complete test execution
        test_execution.status = 'success'
        test_execution.completed_at = datetime.utcnow()
        test_execution.execution_time = (test_execution.completed_at - test_execution.started_at).total_seconds() * 1000
        test_execution.pipeline_results = pipeline_results
        
        # Calculate final metrics
        successful_steps = len([r for r in pipeline_results if r["status"] == "success"])
        test_execution.success_rate = (successful_steps / len(pipeline_results)) * 100
        
        await database.update_test_execution(test_execution)
        
        # Broadcast completion
        await websocket_manager.broadcast_to_user(
            test_execution.user_id,
            {
                "type": "test_completed",
                "payload": test_execution.to_dict()
            }
        )
        
        logger.info(f"Pipeline test {test_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline test {test_id} failed: {e}")
        await fail_test_execution(test_execution, str(e), pipeline_results)

@router.get("/active")
async def get_active_tests(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get all currently active test executions."""
    try:
        active_tests = await database.get_active_test_executions()
        return [test.to_dict() for test in active_tests]
    except Exception as e:
        logger.error(f"Failed to get active tests: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active tests")

@router.get("/history")
async def get_test_history(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get test execution history with filtering."""
    try:
        test_history = await database.get_test_history(
            limit=limit,
            offset=offset,
            status=status
        )
        return [test.to_dict() for test in test_history]
    except Exception as e:
        logger.error(f"Failed to get test history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve test history")

@router.get("/metrics")
async def get_testing_metrics(
    days: int = 7,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive testing metrics and analytics."""
    try:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get test statistics
        total_tests = await database.count_tests_since(since_date)
        successful_tests = await database.count_successful_tests_since(since_date)
        failed_tests = await database.count_failed_tests_since(since_date)
        
        # Calculate success rate
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Get average execution time
        avg_execution_time = await database.get_average_execution_time_since(since_date)
        
        # Get pipeline step statistics
        step_statistics = await database.get_pipeline_step_statistics_since(since_date)
        
        # Get hourly test distribution
        hourly_distribution = await database.get_hourly_test_distribution_since(since_date)
        
        return {
            "period_days": days,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": round(success_rate, 2),
            "average_execution_time_ms": round(avg_execution_time, 2),
            "step_statistics": step_statistics,
            "hourly_distribution": hourly_distribution,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get testing metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve testing metrics")

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_from_websocket)
):
    """WebSocket endpoint for real-time testing updates."""
    await websocket_manager.connect(websocket, current_user.id)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "subscribe_test":
                test_id = message.get("test_id")
                await websocket_manager.subscribe_to_test(websocket, test_id)
                
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, current_user.id)
    except Exception as e:
        logger.error(f"WebSocket error for user {current_user.id}: {e}")
        await websocket_manager.disconnect(websocket, current_user.id)
```

## Database Schema

### Testing Tables
```sql
-- Test executions table
CREATE TABLE test_executions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    test_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    lead_data JSONB NOT NULL,
    pipeline_results JSONB,
    execution_time INTEGER, -- milliseconds
    success_rate DECIMAL(5,2),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_test_executions_user_id ON test_executions(user_id);
CREATE INDEX idx_test_executions_status ON test_executions(status);
CREATE INDEX idx_test_executions_created_at ON test_executions(created_at);
CREATE INDEX idx_test_executions_test_type ON test_executions(test_type);

-- System metrics table
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    metric_unit VARCHAR(20),
    tags JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_metrics_name_timestamp ON system_metrics(metric_name, timestamp);
CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp);

-- Pipeline health checks table
CREATE TABLE pipeline_health_checks (
    id SERIAL PRIMARY KEY,
    component_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time INTEGER, -- milliseconds
    error_message TEXT,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pipeline_health_component ON pipeline_health_checks(component_name);
CREATE INDEX idx_pipeline_health_timestamp ON pipeline_health_checks(timestamp);
```

## Authentication & Authorization

### Role-Based Access Control
```python
from enum import Enum
from typing import List, Optional
from functools import wraps

class UserRole(str, Enum):
    ADMIN = "admin"
    QA_MANAGER = "qa_manager"
    QA_TESTER = "qa_tester"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class Permission(str, Enum):
    # Testing permissions
    RUN_PIPELINE_TESTS = "run_pipeline_tests"
    VIEW_TEST_RESULTS = "view_test_results"
    MANAGE_LEADS = "manage_leads"
    BULK_IMPORT_LEADS = "bulk_import_leads"
    
    # System permissions
    VIEW_SYSTEM_METRICS = "view_system_metrics"
    MANAGE_SYSTEM_CONFIG = "manage_system_config"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    SYSTEM_ADMINISTRATION = "system_administration"

# Role-Permission mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.RUN_PIPELINE_TESTS,
        Permission.VIEW_TEST_RESULTS,
        Permission.MANAGE_LEADS,
        Permission.BULK_IMPORT_LEADS,
        Permission.VIEW_SYSTEM_METRICS,
        Permission.MANAGE_SYSTEM_CONFIG,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_USERS,
        Permission.SYSTEM_ADMINISTRATION
    ],
    UserRole.QA_MANAGER: [
        Permission.RUN_PIPELINE_TESTS,
        Permission.VIEW_TEST_RESULTS,
        Permission.MANAGE_LEADS,
        Permission.BULK_IMPORT_LEADS,
        Permission.VIEW_SYSTEM_METRICS,
        Permission.VIEW_AUDIT_LOGS
    ],
    UserRole.QA_TESTER: [
        Permission.RUN_PIPELINE_TESTS,
        Permission.VIEW_TEST_RESULTS,
        Permission.MANAGE_LEADS
    ],
    UserRole.DEVELOPER: [
        Permission.RUN_PIPELINE_TESTS,
        Permission.VIEW_TEST_RESULTS,
        Permission.VIEW_SYSTEM_METRICS
    ],
    UserRole.VIEWER: [
        Permission.VIEW_TEST_RESULTS,
        Permission.VIEW_SYSTEM_METRICS
    ]
}

def require_permission(permission: Permission):
    """Decorator to require specific permission for endpoint access."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission '{permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def has_permission(user: User, permission: Permission) -> bool:
    """Check if user has specific permission."""
    user_permissions = ROLE_PERMISSIONS.get(user.role, [])
    return permission in user_permissions

# React component for permission checking
@require_permission(Permission.RUN_PIPELINE_TESTS)
@router.post("/run-pipeline")
async def run_pipeline_test(
    test_request: PipelineTestRequest,
    current_user: User = Depends(get_current_user)
):
    # Implementation here
    pass
```

### Frontend Permission Integration
```typescript
// hooks/usePermissions.ts
import { useContext } from 'react';
import { AuthContext } from '@/contexts/AuthContext';

export type Permission = 
  | 'run_pipeline_tests'
  | 'view_test_results'
  | 'manage_leads'
  | 'bulk_import_leads'
  | 'view_system_metrics'
  | 'manage_system_config'
  | 'view_audit_logs'
  | 'manage_users'
  | 'system_administration';

export const usePermissions = () => {
  const { user } = useContext(AuthContext);
  
  const hasPermission = (permission: Permission): boolean => {
    if (!user) return false;
    return user.permissions.includes(permission);
  };
  
  const hasAnyPermission = (permissions: Permission[]): boolean => {
    return permissions.some(permission => hasPermission(permission));
  };
  
  const hasAllPermissions = (permissions: Permission[]): boolean => {
    return permissions.every(permission => hasPermission(permission));
  };
  
  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    permissions: user?.permissions || []
  };
};

// components/PermissionGate.tsx
interface PermissionGateProps {
  permission?: Permission;
  permissions?: Permission[];
  requireAll?: boolean;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const PermissionGate: React.FC<PermissionGateProps> = ({
  permission,
  permissions = [],
  requireAll = false,
  fallback = null,
  children
}) => {
  const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermissions();
  
  let hasAccess = true;
  
  if (permission) {
    hasAccess = hasPermission(permission);
  } else if (permissions.length > 0) {
    hasAccess = requireAll 
      ? hasAllPermissions(permissions)
      : hasAnyPermission(permissions);
  }
  
  return hasAccess ? <>{children}</> : <>{fallback}</>;
};

// Usage in components
<PermissionGate permission="run_pipeline_tests">
  <Button onClick={runTest}>Run Pipeline Test</Button>
</PermissionGate>

<PermissionGate permissions={["manage_leads", "bulk_import_leads"]}>
  <LeadManager onTestLead={handleTestLead} />
</PermissionGate>
```

## Testing Strategy

### Component Testing
```typescript
// __tests__/TestingDashboard.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TestingDashboard } from '@/components/TestingDashboard';
import { AuthProvider } from '@/contexts/AuthContext';
import { WebSocketProvider } from '@/contexts/WebSocketContext';

const mockUser = {
  id: 1,
  name: 'Test User',
  role: 'qa_manager',
  permissions: ['run_pipeline_tests', 'view_test_results', 'manage_leads']
};

const mockSystemStatus = {
  pipeline_health: 'healthy',
  active_tests: 2,
  completed_tests: 45,
  failed_tests: 3,
  system_metrics: {
    cpu_usage: 25,
    memory_usage: 60,
    database_connections: 12,
    queue_depth: 5
  }
};

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <AuthProvider value={{ user: mockUser }}>
      <WebSocketProvider>
        {component}
      </WebSocketProvider>
    </AuthProvider>
  );
};

describe('TestingDashboard', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    global.WebSocket = jest.fn().mockImplementation(() => ({
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      send: jest.fn(),
      close: jest.fn()
    }));
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  test('renders dashboard with system status', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockSystemStatus
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => []
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => []
      });

    renderWithProviders(
      <TestingDashboard user={mockUser} permissions={mockUser.permissions} />
    );

    expect(screen.getByText('Loading testing dashboard...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('LeadShop Testing Interface')).toBeInTheDocument();
    });

    expect(screen.getByText('System Status')).toBeInTheDocument();
    expect(screen.getByText('Active Tests (2)')).toBeInTheDocument();
  });

  test('handles pipeline test execution', async () => {
    const mockTestResponse = {
      test_id: 'test-123',
      status: 'started',
      estimated_duration: '5-8 minutes'
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockSystemStatus
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => []
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => []
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTestResponse
      });

    renderWithProviders(
      <TestingDashboard user={mockUser} permissions={mockUser.permissions} />
    );

    await waitFor(() => {
      expect(screen.getByText('Run Full Pipeline Test')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Run Full Pipeline Test'));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/testing/run-pipeline',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      );
    });
  });

  test('displays permission-based UI elements', () => {
    const viewerUser = {
      ...mockUser,
      role: 'viewer',
      permissions: ['view_test_results']
    };

    renderWithProviders(
      <TestingDashboard user={viewerUser} permissions={viewerUser.permissions} />
    );

    // Viewer should not see run test button
    expect(screen.queryByText('Run Full Pipeline Test')).not.toBeInTheDocument();
    
    // But should see status information
    waitFor(() => {
      expect(screen.getByText('System Status')).toBeInTheDocument();
    });
  });
});

// __tests__/LeadManager.test.tsx
describe('LeadManager', () => {
  test('handles CSV file upload', async () => {
    const mockOnTestLead = jest.fn();
    const csvContent = 'business_name,website_url,email\nTest Corp,https://test.com,test@test.com';
    const file = new File([csvContent], 'leads.csv', { type: 'text/csv' });

    render(<LeadManager onTestLead={mockOnTestLead} permissions={['manage_leads']} />);

    const input = screen.getByTestId('file-upload');
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    });

    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText('Test Corp')).toBeInTheDocument();
    });
  });

  test('validates lead data during import', async () => {
    const mockOnTestLead = jest.fn();
    const invalidCsvContent = 'business_name,website_url,email\n,invalid-url,invalid-email';
    const file = new File([invalidCsvContent], 'leads.csv', { type: 'text/csv' });

    render(<LeadManager onTestLead={mockOnTestLead} permissions={['manage_leads']} />);

    const input = screen.getByTestId('file-upload');
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false,
    });

    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText(/Import Errors/)).toBeInTheDocument();
    });
  });
});
```

### API Testing
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app

client = TestClient(app)

@pytest.fixture
def mock_user():
    return {
        "id": 1,
        "name": "Test User",
        "role": "qa_manager",
        "permissions": ["run_pipeline_tests", "view_test_results"]
    }

@pytest.fixture
def auth_headers(mock_user):
    token = create_test_jwt_token(mock_user)
    return {"Authorization": f"Bearer {token}"}

class TestTestingAPI:
    
    def test_get_system_status(self, auth_headers):
        """Test system status endpoint returns proper format."""
        with patch('api.testing.check_pipeline_health') as mock_health, \
             patch('api.testing.get_system_metrics') as mock_metrics:
            
            mock_health.return_value = "healthy"
            mock_metrics.return_value = {
                "cpu_usage": 25.5,
                "memory_usage": 60.2,
                "database_connections": 10,
                "queue_depth": 3
            }
            
            response = client.get("/api/v1/testing/status", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["pipeline_health"] == "healthy"
            assert "system_metrics" in data
            assert "timestamp" in data
    
    def test_run_pipeline_test_success(self, auth_headers):
        """Test successful pipeline test initiation."""
        test_request = {
            "test_type": "full_pipeline",
            "lead_data": {
                "business_name": "Test Corp",
                "website_url": "https://test.com",
                "email": "test@test.com"
            }
        }
        
        with patch('api.testing.execute_pipeline_test') as mock_execute:
            response = client.post(
                "/api/v1/testing/run-pipeline",
                json=test_request,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "test_id" in data
            assert "estimated_duration" in data
    
    def test_run_pipeline_test_missing_url(self, auth_headers):
        """Test pipeline test with missing website URL."""
        test_request = {
            "test_type": "full_pipeline",
            "lead_data": {
                "business_name": "Test Corp",
                "email": "test@test.com"
            }
        }
        
        response = client.post(
            "/api/v1/testing/run-pipeline",
            json=test_request,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Website URL is required" in response.json()["detail"]
    
    def test_get_test_history_with_filtering(self, auth_headers):
        """Test test history endpoint with status filtering."""
        with patch('database.get_test_history') as mock_history:
            mock_history.return_value = [
                {
                    "id": "test-1",
                    "status": "success",
                    "execution_time": 300000,
                    "created_at": "2025-01-01T10:00:00Z"
                }
            ]
            
            response = client.get(
                "/api/v1/testing/history?status=success&limit=10",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "success"
    
    def test_unauthorized_access(self):
        """Test API access without authentication."""
        response = client.get("/api/v1/testing/status")
        assert response.status_code == 401
    
    def test_insufficient_permissions(self):
        """Test API access with insufficient permissions."""
        viewer_user = {
            "id": 2,
            "name": "Viewer User",
            "role": "viewer",
            "permissions": ["view_test_results"]
        }
        
        token = create_test_jwt_token(viewer_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        test_request = {
            "test_type": "full_pipeline",
            "lead_data": {
                "business_name": "Test Corp",
                "website_url": "https://test.com",
                "email": "test@test.com"
            }
        }
        
        response = client.post(
            "/api/v1/testing/run-pipeline",
            json=test_request,
            headers=headers
        )
        
        assert response.status_code == 403
        assert "Permission 'run_pipeline_tests' required" in response.json()["detail"]

@pytest.mark.asyncio
class TestPipelineExecution:
    
    async def test_complete_pipeline_execution(self):
        """Test complete pipeline execution with all steps."""
        test_execution = {
            "id": "test-123",
            "user_id": 1,
            "test_type": "full_pipeline",
            "lead_data": {
                "business_name": "Test Corp",
                "website_url": "https://test.com",
                "email": "test@test.com"
            },
            "status": "pending"
        }
        
        # Mock all pipeline step functions
        with patch('api.testing.test_s3_integration') as mock_s3, \
             patch('api.testing.test_lead_data_model') as mock_lead, \
             patch('api.testing.test_assessment_orchestrator') as mock_orchestrator:
            
            # Setup successful responses
            mock_s3.return_value = {"status": "success", "duration": 100, "details": {}}
            mock_lead.return_value = {"status": "success", "duration": 50, "details": {}}
            mock_orchestrator.return_value = {"status": "success", "duration": 200, "details": {}}
            
            from api.testing import execute_pipeline_test
            await execute_pipeline_test(test_execution["id"])
            
            # Verify all steps were called
            mock_s3.assert_called_once()
            mock_lead.assert_called_once()
            mock_orchestrator.assert_called_once()
    
    async def test_pipeline_failure_handling(self):
        """Test pipeline execution with step failure."""
        test_execution = {
            "id": "test-456",
            "user_id": 1,
            "test_type": "full_pipeline",
            "lead_data": {
                "business_name": "Test Corp",
                "website_url": "https://invalid-url.com",
                "email": "test@test.com"
            },
            "status": "pending"
        }
        
        with patch('api.testing.test_s3_integration') as mock_s3, \
             patch('api.testing.test_lead_data_model') as mock_lead:
            
            # Setup failure in second step
            mock_s3.return_value = {"status": "success", "duration": 100, "details": {}}
            mock_lead.return_value = {"status": "failed", "duration": 50, "details": {"error": "Invalid data"}}
            
            from api.testing import execute_pipeline_test
            await execute_pipeline_test(test_execution["id"])
            
            # Verify execution stopped after failure
            mock_s3.assert_called_once()
            mock_lead.assert_called_once()
```

## Deployment Configuration

### Docker Setup
```dockerfile
# Dockerfile for testing interface
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

### Environment Configuration
```bash
# Testing interface environment variables
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/leadshop_test

# Redis (for WebSocket and caching)
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=your-jwt-secret
JWT_EXPIRES_IN=24h

# Testing configuration
MAX_CONCURRENT_TESTS=5
TEST_TIMEOUT_SECONDS=600
ENABLE_TEST_HISTORY=true
TEST_HISTORY_RETENTION_DAYS=30

# Lead import limits
MAX_IMPORT_FILE_SIZE_MB=10
MAX_LEADS_PER_IMPORT=1000
ENABLE_BULK_IMPORT=true

# Monitoring
ENABLE_METRICS_COLLECTION=true
METRICS_COLLECTION_INTERVAL=60
PROMETHEUS_ENDPOINT=http://localhost:9090
```

### Docker Compose
```yaml
# docker-compose.testing.yml
version: '3.8'

services:
  testing-interface:
    build:
      context: .
      dockerfile: Dockerfile.testing
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_BASE_URL=http://api:8000
      - NEXT_PUBLIC_WS_URL=ws://api:8000
      - DATABASE_URL=postgresql://postgres:password@db:5432/leadshop_test
      - REDIS_URL=redis://redis:6379
    depends_on:
      - api
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
    networks:
      - leadshop-network

  api:
    build:
      context: ../api
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/leadshop_test
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    networks:
      - leadshop-network

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=leadshop_test
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - leadshop-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - leadshop-network

volumes:
  postgres_data:
  redis_data:

networks:
  leadshop-network:
    driver: bridge
```

## Success Criteria

### Functional Requirements ✅
- [x] Complete pipeline testing coverage for all 12 PRPs
- [x] Real-time test execution monitoring with WebSocket updates
- [x] Bulk lead import and validation with CSV/Excel support
- [x] Comprehensive business metrics visualization
- [x] Role-based access control with permission management
- [x] System health monitoring and performance metrics

### Performance Requirements ✅
- [x] Dashboard load time < 2 seconds
- [x] Real-time updates with <500ms latency
- [x] Support for 1000+ lead batch processing
- [x] Concurrent test execution (up to 5 simultaneous tests)
- [x] Responsive design for mobile and desktop

### Quality Requirements ✅
- [x] 100% test coverage for critical components
- [x] Comprehensive error handling and user feedback
- [x] Accessibility compliance (WCAG 2.1 AA)
- [x] Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
- [x] Professional UI/UX with intuitive navigation

### Integration Requirements ✅
- [x] Complete integration with all pipeline components (PRPs 000-012)
- [x] WebSocket real-time communication
- [x] Database persistence for audit trails
- [x] Authentication and authorization system
- [x] Metrics collection and monitoring integration

## Risk Mitigation

### Performance Risks
- **Risk**: Dashboard performance degradation with large datasets
- **Mitigation**: Pagination, virtualization, and intelligent caching
- **Monitoring**: Performance metrics and user experience tracking

### Security Risks
- **Risk**: Unauthorized access to testing interface
- **Mitigation**: Role-based access control and JWT authentication
- **Monitoring**: Audit logging and security event tracking

### Usability Risks
- **Risk**: Complex interface overwhelming users
- **Mitigation**: Progressive disclosure and contextual help
- **Monitoring**: User feedback collection and usability testing

### Reliability Risks
- **Risk**: WebSocket connection failures affecting real-time updates
- **Mitigation**: Automatic reconnection and fallback polling
- **Monitoring**: Connection health tracking and alerting

## Acceptance Criteria Validation

✅ **Complete Testing Coverage**: Interface provides testing for all 12 pipeline components  
✅ **Real-time Monitoring**: WebSocket-based real-time updates for test execution  
✅ **Lead Management**: Bulk import/export with validation and deduplication  
✅ **Performance Metrics**: Comprehensive visualization of system and business metrics  
✅ **Access Control**: Role-based permissions with secure authentication  
✅ **System Health**: Real-time monitoring of all pipeline components  
✅ **Responsive Design**: Mobile-friendly interface with cross-browser support  
✅ **Data Persistence**: Complete audit trail for all testing activities  

## Rollback Strategy

### Emergency Rollback Procedures
1. **Interface Issues**: Revert to previous Docker image via container orchestration
2. **Database Problems**: Restore from backup with point-in-time recovery
3. **Authentication Failures**: Fallback to basic authentication mode
4. **Performance Issues**: Enable performance monitoring and resource limiting

### Data Recovery
- All test executions stored with complete audit trail
- Lead data backed up before bulk operations
- System metrics retained for historical analysis
- WebSocket event logging for debugging and replay

---

**Implementation Timeline**: 10-14 days  
**Total Effort**: 60-80 hours  
**Team Size**: 3-4 developers (Full-stack, Frontend, Backend, QA)  
**Confidence Level**: 90% (comprehensive system with proven technology stack)