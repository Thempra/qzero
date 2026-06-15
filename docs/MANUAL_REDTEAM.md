# QZero Operations Manual: Red Team (Offense)

## ⚔️ Introduction

QZero introduces a new defensive paradigm: **Quantum-Probabilistic Detection**. Traditional evasion techniques (obfuscation, timing jitter, fragmentation) designed to bypass static rules (Snort/Yara) may **fail** against QZero because it models the *latent manifold* of normal traffic.

**Your Goal:** Understand the quantum decision boundary and craft traffic that stays within the "normal" Hilbert space.

## 🎯 The Adversarial Challenge

The QZero engine (specifically the QI-VAE) learns a compact representation of "normal" traffic. Deviations from this representation create a "Reconstruction Error".

**The Game:** Minimizing Reconstruction Error while executing malicious actions.

## 🕵️ Evasion Techniques & Testing

### 1. Quantum Gradient Attack (Theory)

If you have black-box access to the QZero score (e.g., via a test instance), you can perform a gradient descent attack on your traffic parameters.

*   **Vector:** Packet Size + Inter-arrival Time.
*   **Method:** Adjust packet padding and sleep times until `QAS < 0.70`.

### 2. "Living off the Land" (Quantum Edition)

QZero learns the shape of *existing* traffic.
*   **Strategy:** Mimic the statistical moments (mean, variance, kurtosis) of the target's dominant traffic (e.g., HTTPS video streaming or SMB file transfers).
*   **Tooling:** Use `scripts/replay_traffic.py` to test if your C2 profile matches a recording of legitimate traffic.

### 3. Model Poisoning

If the Blue Team has auto-retraining enabled:
1.  Slowly inject "noise" traffic that looks slightly like your C2 over weeks.
2.  The QZero model will drift to accept this noise as "normal".
3.  Execute the attack.

## 🧪 Testing Your Implant

We provide a utility to test your C2 profiles against a local QZero instance before deployment.

**Prerequisite:** A captured PCAP of your C2 beaconing.

```bash
# Replay your C2 traffic against the detector
python scripts/adversarial_test.py \
  --pcap c2_cobalt_strike.pcap \
  --target http://localhost:8000 \
  --mode evasion
```

**Output:**

```text
[+] Analyzing flow 1... QAS: 0.88 (DETECTED)
[+] Analyzing flow 2... QAS: 0.91 (DETECTED)
[!] Evasion Failed.
[i] Suggestion: Increase jitter variance by 15% to match 'HTTP Browsing' profile.
```

## ⚠️ Detection Surfaces

QZero is particularly sensitive to:

*   **Periodicity:** Perfectly regular beacons (even with minor jitter) stand out in the frequency domain features.
*   **Burstiness:** Large data exfiltration spikes.
*   **Protocol Anomalies:** SSH tunneling over DNS or ICMP.

## 🧰 Toolkit Integration

*   **Cobalt Strike:** Use `Malleable C2` profiles that mimic high-entropy legitimate traffic (e.g., TLS handshake heavy).
*   **Sliver:** Enable `jitter` and restrict block sizes to standard MTU distributions.

---
**Note:** This tool is provided for authorized Red Team engagements to validate defensive posture.
