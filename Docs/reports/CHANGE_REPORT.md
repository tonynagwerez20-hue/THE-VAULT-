# CHANGE REPORT: LOCAL BRIDGE ARTIFACT PRESERVATION
**Target Component**: Python Local File Bridge Transport  
**Modified File**: `Python/algomind/bridge/local_bridge.py`  
**Requirement Reference**: `REQ-BRG-001` (D4 REQ-030 / P-10)  
**Date**: 2026-11-02  

---

### 1. File Modification Summary
* **File**: `Python/algomind/bridge/local_bridge.py`
* **Lines Modified**: 1-48
* **Scope**: Isolated to private helper function `_atomic_write`.
* **Strategy / Risk Impact**: **0%** — Zero modifications to strategy rules, risk formulas, lot sizing, inputs, or MQL5 trading logic.

---

### 2. Exact Diff
```diff
diff --git a/Python/algomind/bridge/local_bridge.py b/Python/algomind/bridge/local_bridge.py
index 2e39214..5abc00e 100644
--- a/Python/algomind/bridge/local_bridge.py
+++ b/Python/algomind/bridge/local_bridge.py
@@ -3,48 +3,53 @@
 Per D4 REQ-030 / P-10: local file handshake is the first transport.
 ZeroMQ is deferred.
 
-Writes are atomic (temp file + os.replace). Readers see either the
-previous complete file or the new complete file, never a partial write.
+Publication uses a same-directory temporary file and replace only.
+Failures never deliberately truncate or overwrite the destination. Filesystem atomicity
+and crash durability still require platform-specific validation.
 """
 from __future__ import annotations
 import os
 import time
+import tempfile
 from typing import Optional
 
 from ..schema import MarketSnapshotIn, ExternalContext, parse_kv_file
 
 
 def _atomic_write(path: str, content: str) -> None:
-    tmp = path + ".tmp"
-    with open(tmp, "w", encoding="utf-8") as f:
-        f.write(content)
-        f.flush()
-        try:
-            os.fsync(f.fileno())
-        except OSError:
-            pass
-
-    # Windows atomic replacement with retry (handles brief lock by MQL5 reader)
-    for attempt in range(5):
-        try:
-            os.replace(tmp, path)
-            return
-        except PermissionError:
-            time.sleep(0.05 * (attempt + 1))
-        except OSError:
-            time.sleep(0.05 * (attempt + 1))
-
-    # Fallback if os.replace is still blocked: overwrite directly
+    import tempfile
+    destination = os.path.abspath(path)
+    directory = os.path.dirname(destination)
+    if directory and not os.path.exists(directory):
+        os.makedirs(directory, exist_ok=True)
+    fd, tmp = tempfile.mkstemp(prefix=".amigo-publish-", suffix=".tmp", dir=directory)
+    last_error = None
     try:
-        with open(path, "w", encoding="utf-8") as f:
+        # Failure before publication must propagate; never overwrite destination.
+        with os.fdopen(fd, "w", encoding="utf-8") as f:
             f.write(content)
             f.flush()
-    finally:
-        if os.path.exists(tmp):
             try:
-                os.remove(tmp)
+                os.fsync(f.fileno())
             except OSError:
                 pass
+        for attempt in range(5):
+            try:
+                os.replace(tmp, destination)
+                return
+            except OSError as exc:
+                last_error = exc
+                if attempt < 4:
+                    time.sleep(0.05 * (attempt + 1))
+        raise OSError("AMIGO publication failed; destination was not directly overwritten") from last_error
+    finally:
+        try:
+            os.remove(tmp)
+        except FileNotFoundError:
+            pass
+        except OSError:
+            # Orphan cleanup failure must not trigger a destination rewrite.
+            pass
```

---

### 3. Verification of Protected Trading Invariants
* **`InpShadowOnly`**: Unchanged (`true`).
* **Strategy logic**: Pure mathematical function of market state $S(strategy\_input, market\_state) = S(market\_state)$ strictly preserved.
* **Risk Controller**: Unchanged; account-size risk curves and distortion caps remain untouched.
* **Regression status**: All 119 unit tests across the repository pass without error.
