# Per-repo fleet start config for pdf-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'pdf-mcp'
    BackendPort  = 11131
    FrontendPort = 11130
    HealthPath   = '/api/health'
    WebRoot      = 'webapp'
    Backend = @{
        Kind       = 'module-serve'
        Module     = 'pdf_mcp'
        SyncExtras = @('dev')
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
