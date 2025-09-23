# Outstanding Issues
### Docling:
Docling has an issue where subsequent use would result in longer processing time for certain devices. Some fixes are available but the problem would come back after a while.
If you wish to temporarily resolve the issue, consider the following solutions

1. This may need you to update other libraries as the version of torch used is 2.4.0
```
Install torch==2.5.1
```
2. The second command is to update the library installed in the first command
```
sudo apt-get install build-essential ninja-build cmake
```
OR
```
sudo apt update
sudo apt install build-essential cmake gcc g++ -y
```

3. Running top in terminal seems to fix any extended processing time
```
top
```
