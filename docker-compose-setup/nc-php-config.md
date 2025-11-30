# PHP config setup
  - these are changes youll have to make to the ```config.php``` file in ```/data/config/```
## changes to tursted domains for access:
- these will vary depending on your setup
```
  'trusted_domains' => 
  array (
    0 => 'localhost',
    1 => '123.123.123.*',
    2 => 'serverdomain.local',
    3 => 'YOURDOMAIN.ZY'
  ),
  ```
## Add these entries:
  ```
  'enable_previews' => true,
  'preview_concurrency_new' => 5,
  'preview_max_x' => 1080,
  'preview_max_memory' => 2000,
  'preview_max_filesize_image' => 1000,
  'max_file_conversion_filesize' => 1000,
  'maintenance_window_start' => 3,
```