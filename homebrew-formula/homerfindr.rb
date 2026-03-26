class Homerfindr < Formula
  desc "Universal home search aggregator — find homes across all platforms in one place"
  homepage "https://github.com/iamtr0n/HomerFindr"
  url "https://github.com/iamtr0n/HomerFindr/archive/refs/heads/main.tar.gz"
  version "1.1.0"
  # Update sha256 after pinning a release tag:
  #   curl -sL https://github.com/iamtr0n/HomerFindr/archive/refs/heads/main.tar.gz | shasum -a 256
  sha256 :no_check

  depends_on "node"
  depends_on "python@3.11"

  def install
    # Keep the full repo structure in libexec — FastAPI needs frontend/dist/ next to the source
    libexec.install Dir["*"]

    # Build the React dashboard
    cd libexec/"frontend" do
      system "npm", "install", "--silent"
      system "npm", "run", "build", "--silent"
    end

    # Create a virtualenv inside libexec and install the Python package
    python = Formula["python@3.11"].opt_bin/"python3.11"
    system python, "-m", "venv", libexec/".venv"
    system libexec/".venv/bin/pip", "install", "--quiet", "--upgrade", "pip"
    system libexec/".venv/bin/pip", "install", "--quiet", "-e", libexec.to_s

    # Wrapper scripts — cd to libexec so relative paths (frontend/dist) resolve correctly
    (bin/"homesearch").write <<~EOS
      #!/bin/bash
      cd "#{libexec}" && exec "#{libexec}/.venv/bin/homesearch" "$@"
    EOS
    (bin/"homerfindr").write <<~EOS
      #!/bin/bash
      cd "#{libexec}" && exec "#{libexec}/.venv/bin/homerfindr" "$@"
    EOS
    chmod 0755, bin/"homesearch"
    chmod 0755, bin/"homerfindr"
  end

  service do
    run        [opt_bin/"homesearch", "serve"]
    working_dir opt_libexec
    log_path   var/"log/homerfindr.log"
    error_log_path var/"log/homerfindr.err"
    keep_alive true
    run_at_load true
  end

  def caveats
    <<~EOS
      HomerFindr is installed!

      Start (auto-restarts on login):
        brew services start homerfindr

      Run once:
        homerfindr serve

      Then open → http://127.0.0.1:8000

      Optional SMS alerts — add your Zapier webhook:
        mkdir -p ~/.homesearch
        echo 'ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/...' >> ~/.homesearch/.env

    EOS
  end

  test do
    assert_match "homesearch", shell_output("#{bin}/homerfindr --help")
  end
end
