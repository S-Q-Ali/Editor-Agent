const { spawn } = require('child_process')
const http = require('http')
const path = require('path')

class PythonManager {
  constructor() {
    this.process = null
    this.port = 8000
    this.isRunning = false
  }

  async start(executablePath) {
    if (this.process) {
      this.stop()
    }

    let cmd, args, options

    if (executablePath) {
      cmd = executablePath
      args = []
      options = {
        env: {
          ...process.env,
          BACKEND_PORT: String(this.port),
          BACKEND_HOST: '127.0.0.1',
          DEBUG: 'false',
        },
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      }
    } else {
      const pythonDir = path.join(__dirname, '..', 'backend')
      cmd = 'python'
      args = ['-m', 'app.main']
      options = {
        cwd: pythonDir,
        env: {
          ...process.env,
          BACKEND_PORT: String(this.port),
          BACKEND_HOST: '127.0.0.1',
          DEBUG: 'false',
        },
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      }
    }

    this.process = spawn(cmd, args, options)
    this.isRunning = true

    this.process.stdout?.on('data', (data) => {
      console.log(`[Python] ${data.toString().trim()}`)
    })

    this.process.stderr?.on('data', (data) => {
      console.log(`[Python] ${data.toString().trim()}`)
    })

    this.process.on('close', (code) => {
      console.log(`Python process exited with code ${code}`)
      this.isRunning = false
    })

    this.process.on('error', (err) => {
      console.error('Failed to start Python process:', err)
      this.isRunning = false
    })
  }

  async waitForReady(maxAttempts = 30) {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const ready = await this.healthCheck()
        if (ready) return true
      } catch {
        // not ready yet
      }
      await new Promise((r) => setTimeout(r, 1000))
    }
    throw new Error('Python backend failed to start within 30 seconds')
  }

  healthCheck() {
    return new Promise((resolve, reject) => {
      const req = http.get(
        `http://127.0.0.1:${this.port}/api/health`,
        { timeout: 3000 },
        (res) => {
          let data = ''
          res.on('data', (chunk) => (data += chunk))
          res.on('end', () => {
            resolve(res.statusCode === 200)
          })
        }
      )
      req.on('error', reject)
      req.on('timeout', () => {
        req.destroy()
        reject(new Error('timeout'))
      })
    })
  }

  async stop() {
    if (this.process && this.isRunning) {
      return new Promise((resolve) => {
        this.process.once('close', () => resolve())
        this.process.kill('SIGTERM')
        setTimeout(() => {
          if (this.isRunning) {
            this.process.kill('SIGKILL')
          }
          resolve()
        }, 5000)
      })
    }
  }

  getPort() {
    return this.port
  }
}

module.exports = PythonManager
