diff --git a/docker/util/config_stripper.py b/docker/util/config_stripper.py
index 6f8bb33..2424e04 100644
--- a/docker/util/config_stripper.py
+++ b/docker/util/config_stripper.py
@@ -28,8 +28,6 @@ import threading
 
 _TIMESTAMP = '1970-01-01T00:00:00Z'
 
-WHITELISTED_PREFIXES = ['sha256:', 'manifest', 'repositories']
-
 _BUF_SIZE = 4096
 
 def main():
@@ -70,7 +68,7 @@ def strip_tar(input, output):
         # that symlinks to a lower layer that hasn't been extracted yet. Just
         # reversing the iteration order avoids this problem.
         for layer in reversed(image['Layers']):
-          (new_layer_name, new_diff_id) = strip_layer(os.path.join(tempdir, layer))
+          (new_layer_name, new_diff_id) = strip_layer(tempdir, layer)
 
           new_layers.append(new_layer_name)
           new_diff_ids.append(new_diff_id)
@@ -83,8 +81,8 @@ def strip_tar(input, output):
         image['Layers'] = new_layers
 
         config = image['Config']
-        cfg_path = os.path.join(tempdir, config)
-        new_cfg_path = strip_config(cfg_path, new_diff_ids)
+
+        new_cfg_path = strip_config(tempdir, config, new_diff_ids)
 
         # Update the name of the config in the metadata object
         # to match it's new digest.
@@ -98,10 +96,9 @@ def strip_tar(input, output):
     files_to_add = []
     for root, _, files in os.walk(tempdir):
         for f in files:
-            if os.path.basename(f).startswith(tuple(WHITELISTED_PREFIXES)):
-                name = os.path.join(root, f)
-                os.utime(name, (0,0))
-                files_to_add.append(name)
+            name = os.path.join(root, f)
+            os.utime(name, (0,0))
+            files_to_add.append(name)
 
     with tarfile.open(name=output, mode='w') as ot:
         for f in sorted(files_to_add):
@@ -112,10 +109,11 @@ def strip_tar(input, output):
     shutil.rmtree(tempdir)
     return 0
 
-def strip_layer(path):
+def strip_layer(work_dir, layer):
     # The original layer tar is of the form <random string>/layer.tar, the
     # working directory is one level up from where layer.tar is.
-    original_dir = os.path.normpath(os.path.join(os.path.dirname(path), '..'))
+    path = os.path.join(work_dir, layer)
+    original_dir = os.path.dirname(path)
 
     # Write compressed tar to a temporary name. We'll rename it to the correct
     # name after we compute the hash.
@@ -206,14 +204,15 @@ def strip_layer(path):
     diffid = 'sha256:%s' % uncompressed_sha.hexdigest()
 
     # Rename into correct location now that we know the hash.
-    new_name = 'sha256:%s' % compressed_sha.hexdigest()
-    os.rename(gz_out.name, os.path.join(original_dir, new_name))
+    new_name = os.path.join(original_dir, compressed_sha.hexdigest())
+    os.rename(gz_out.name, new_name)
 
-    shutil.rmtree(os.path.dirname(path))
-    return (new_name, diffid)
+    os.remove(path)
+    return (os.path.relpath(new_name, work_dir), diffid)
 
 
-def strip_config(path, new_diff_ids):
+def strip_config(work_dir, config, new_diff_ids):
+    path = os.path.join(work_dir, config)
     with open(path, 'r') as f:
         config = json.load(f)
     config['created'] = _TIMESTAMP
@@ -239,9 +238,9 @@ def strip_config(path, new_diff_ids):
 
     # Calculate the new file path
     sha = hashlib.sha256(config_str.encode("utf-8")).hexdigest()
-    new_path = 'sha256:%s' % sha
-    os.rename(path, os.path.join(os.path.dirname(path), new_path))
-    return new_path
+    new_path = os.path.join(os.path.dirname(path), sha)
+    os.rename(path, new_path)
+    return os.path.relpath(new_path, work_dir)
 
 
 if __name__ == "__main__":
