// ─────────────────────────────────────────────────────────────────────────────
// Smart Job Agent V2 — Jenkins CI/CD Pipeline
//
// Stages:
//   1. Checkout        — pull code from SCM
//   2. Python Lint     — flake8 on backend_v2/
//   3. Backend Tests   — pytest (unit + integration)
//   4. Frontend Lint   — eslint on frontend/src/
//   5. Frontend Build  — next build (production bundle)
//   6. Security Scan   — bandit (Python SAST) + npm audit
//   7. GDPR Check      — verify no PII in logs / hardcoded secrets
//   8. Docker Build    — build backend + frontend images
//   9. Deploy Staging  — deploy to staging environment
//  10. Smoke Tests     — hit /v2/health and key endpoints
//  11. Deploy Prod     — promote to production (manual approval gate)
//
// Required Jenkins credentials:
//   GEMINI_API_KEY_CRED  — Secret Text
//   DOCKER_HUB_CRED      — Username/Password
//   RAILWAY_TOKEN_CRED   — Secret Text (staging/prod deploy)
// ─────────────────────────────────────────────────────────────────────────────

pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        PYTHON_BIN     = '.venv/Scripts/python.exe'  // Windows agent
        PIP_BIN        = '.venv/Scripts/pip.exe'
        NODE_ENV       = 'test'
        STAGING_URL    = 'https://smart-job-agent-staging.railway.app'
        PROD_URL       = 'https://smart-job-agent.railway.app'
        IMAGE_BACKEND  = "smartjobagent/backend-v2:${env.BUILD_NUMBER}"
        IMAGE_FRONTEND = "smartjobagent/frontend:${env.BUILD_NUMBER}"
    }

    stages {

        // ── Stage 1: Checkout ─────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                echo "Branch: ${env.GIT_BRANCH} | Commit: ${env.GIT_COMMIT[0..7]}"
            }
        }

        // ── Stage 2: Python Environment ───────────────────────────────────────
        stage('Python Setup') {
            steps {
                bat 'python -m venv .venv || true'
                bat "${PIP_BIN} install -r requirements_v2.txt --quiet"
                bat "${PIP_BIN} install flake8 bandit pytest pytest-asyncio pytest-cov --quiet"
            }
        }

        // ── Stage 3: Python Lint ──────────────────────────────────────────────
        stage('Python Lint') {
            steps {
                bat "${PYTHON_BIN} -m flake8 backend_v2/ --max-line-length=120 --exclude=__pycache__,.venv --statistics"
            }
            post {
                failure {
                    echo 'Lint failed — fix style issues before merging.'
                }
            }
        }

        // ── Stage 4: Backend Tests ────────────────────────────────────────────
        stage('Backend Tests') {
            environment {
                GEMINI_API_KEY     = credentials('GEMINI_API_KEY_CRED')
                DATABASE_URL       = 'postgresql+asyncpg://smartjob:smartjob@localhost:5432/smartjob_test'
                REDIS_URL          = 'redis://localhost:6379/1'
                LLM_MODEL_HEAVY    = 'gemini-2.5-flash-lite'
                LLM_MODEL_FAST     = 'gemini-2.5-flash-lite'
            }
            steps {
                bat """
                    ${PYTHON_BIN} -m pytest tests/ ^
                        --cov=backend_v2 ^
                        --cov-report=xml:coverage.xml ^
                        --cov-report=term-missing ^
                        --tb=short ^
                        -q
                """
            }
            post {
                always {
                    junit 'tests/reports/*.xml'
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')]
                }
            }
        }

        // ── Stage 5: Security Scan (SAST + deps) ─────────────────────────────
        stage('Security Scan') {
            parallel {
                stage('Bandit — Python SAST') {
                    steps {
                        bat """
                            ${PYTHON_BIN} -m bandit -r backend_v2/ ^
                                -ll ^
                                --exclude backend_v2/tests ^
                                -f json -o bandit-report.json || true
                        """
                        script {
                            def report = readJSON file: 'bandit-report.json'
                            def highSeverity = report.results.findAll { it.issue_severity == 'HIGH' }
                            if (highSeverity.size() > 0) {
                                error "Bandit found ${highSeverity.size()} HIGH severity issues — pipeline blocked."
                            }
                        }
                    }
                }
                stage('npm audit') {
                    steps {
                        dir('frontend') {
                            bat 'npm audit --audit-level=high'
                        }
                    }
                }
            }
        }

        // ── Stage 6: GDPR / Responsible AI Compliance Check ──────────────────
        stage('GDPR & Responsible AI Check') {
            steps {
                script {
                    // Verify no hardcoded API keys or PII patterns in source
                    def violations = []

                    // Check for hardcoded API key patterns
                    def apiKeyPattern = bat(
                        script: 'findstr /r /s "AIzaSy[A-Za-z0-9_-]\\{35\\}" backend_v2\\*.py 2>nul',
                        returnStdout: true
                    ).trim()
                    if (apiKeyPattern) {
                        violations << "Hardcoded Gemini API key detected in source"
                    }

                    // Check that AI transparency endpoint exists
                    def transparencyRoute = bat(
                        script: 'findstr /s "ai/transparency" backend_v2\\main.py',
                        returnStdout: true
                    ).trim()
                    if (!transparencyRoute) {
                        violations << "Missing /v2/ai/transparency endpoint (EU AI Act Article 13)"
                    }

                    // Check GDPR delete endpoint exists
                    def gdprDeleteRoute = bat(
                        script: 'findstr /s "gdpr/my-data" backend_v2\\main.py',
                        returnStdout: true
                    ).trim()
                    if (!gdprDeleteRoute) {
                        violations << "Missing GDPR right-to-erasure endpoint (Article 17)"
                    }

                    if (violations) {
                        error "GDPR/Responsible AI violations:\n${violations.join('\n')}"
                    }
                    echo "GDPR & Responsible AI checks passed."
                }
            }
        }

        // ── Stage 7: Frontend Build ───────────────────────────────────────────
        stage('Frontend Build') {
            steps {
                dir('frontend') {
                    bat 'npm ci --silent'
                    bat 'npm run lint'
                    bat 'npm run build'
                }
            }
            post {
                success {
                    archiveArtifacts artifacts: 'frontend/.next/**', fingerprint: true
                }
            }
        }

        // ── Stage 8: Docker Build ─────────────────────────────────────────────
        stage('Docker Build') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'DOCKER_HUB_CRED',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    bat "docker login -u %DOCKER_USER% -p %DOCKER_PASS%"
                    bat "docker build -f Dockerfile.backend -t %IMAGE_BACKEND% ."
                    bat "docker build -f frontend/Dockerfile -t %IMAGE_FRONTEND% ./frontend"
                    bat "docker push %IMAGE_BACKEND%"
                    bat "docker push %IMAGE_FRONTEND%"
                }
            }
        }

        // ── Stage 9: Deploy to Staging ────────────────────────────────────────
        stage('Deploy Staging') {
            when { branch 'develop' }
            steps {
                withCredentials([string(credentialsId: 'RAILWAY_TOKEN_CRED', variable: 'RAILWAY_TOKEN')]) {
                    bat "railway up --service backend-v2-staging --detach"
                }
            }
        }

        // ── Stage 10: Smoke Tests ─────────────────────────────────────────────
        stage('Smoke Tests') {
            when { branch 'develop' }
            steps {
                script {
                    sleep(time: 20, unit: 'SECONDS')
                    def health = bat(
                        script: "curl -sf %STAGING_URL%/v2/health",
                        returnStdout: true
                    ).trim()
                    if (!health.contains('"status":"ok"')) {
                        error "Staging health check failed: ${health}"
                    }
                    echo "Staging smoke tests passed."
                }
            }
        }

        // ── Stage 11: Deploy Production (manual gate) ─────────────────────────
        stage('Deploy Production') {
            when { branch 'main' }
            steps {
                input(
                    message: "Deploy build #${env.BUILD_NUMBER} to PRODUCTION?",
                    ok: "Deploy",
                    submitter: "varun,lead-engineer"
                )
                withCredentials([string(credentialsId: 'RAILWAY_TOKEN_CRED', variable: 'RAILWAY_TOKEN')]) {
                    bat "railway up --service backend-v2-prod --detach"
                }
                echo "Production deployment complete: ${PROD_URL}"
            }
        }

    }

    // ── Post-pipeline actions ─────────────────────────────────────────────────
    post {
        always {
            cleanWs()
        }
        success {
            echo "Pipeline passed — build #${env.BUILD_NUMBER} on ${env.GIT_BRANCH}"
        }
        failure {
            mail(
                to: 'kondapallivarun69@gmail.com',
                subject: "FAILED: Smart Job Agent build #${env.BUILD_NUMBER}",
                body: "Branch: ${env.GIT_BRANCH}\nStage failed — check: ${env.BUILD_URL}"
            )
        }
    }
}
