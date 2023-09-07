| Option Combination                     | Expected Behavior                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------------ |
| No options                             | Create new alarms for all volumes, skip alarms that already exist.                         |
| `--tag=<tag_name>`                     | Create new alarms only for volumes with the specified tag, skip alarms that already exist. |
| `--refresh`                            | Update existing alarms for all volumes.                                                    |
| `--refresh --tag=<tag_name>`           | Update existing alarms only for volumes with the specified tag.                            |
| `--tagless`                            | No effect when used alone.                                                                 |
| `--refresh --tagless`                  | No effect when used alone, needs `--tag` to function.                                      |
| `--refresh --tag=<tag_name> --tagless` | Update existing alarms for volumes with the specified tag and for tagless volumes.         |
