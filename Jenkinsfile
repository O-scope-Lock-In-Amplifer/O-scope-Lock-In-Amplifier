def pkg_name = "o_scope_lock_in_amplifier"  // TODO: If you have multiple top-level packages, this file will need some changes.
def py_ver = "3.10"

pipeline {
    agent any

    stages {
		stage('Setup')
		{
			steps {
			    script
			    {
                    if (env.BRANCH_NAME == "master" || env.BRANCH_NAME == "develop") {
						// If we are on a core branch, totally wipe out everything
                        deleteDir()
						scm.extensions << [$class: 'CloneOption', shallow: false]
						checkout scm
                    }
                }
				bat """py -${py_ver} -m pip install virtualenv
					py -${py_ver} -m venv .venv"""
				/* TODO: Set up in-Jenkins dependencies here.
				fileOperations([fileDeleteOperation(includes: "*.whl")])
				copyArtifacts filter: 'dist/*.whl', fingerprintArtifacts: true, flatten: true, projectName: '/FOLDER/Project/branch', selector: lastSuccessful()
				bat '''for /r "%CD%" %%a in (.\\*.whl) do set p=%%~dpnxa
					.\\.venv\\Scripts\\activate & pip install %p%'''
				*/
				bat 'git submodule update --init --recursive'
				bat '.venv\\Scripts\\activate & pip install -e .[dev]'
				bat '.venv\\Scripts\\activate & python -m setuptools_scm > vers.txt'
				script {
					def vers = readFile('vers.txt').trim()
					echo "Building for version: ${vers}"
					currentBuild.displayName = vers
				}
			}
		}
        stage('Run Tests') {
            steps {
				bat '.venv\\Scripts\\activate & python tasks.py check_formatting'
				bat '.venv\\Scripts\\activate & python tasks.py run_tests'
            }
        }
		// TODO: Disable docs build if you aren't going to use Sphinx
        stage('Build Docs') {
            steps {
				bat '.venv\\Scripts\\activate & python tasks.py build_docs'
				archiveArtifacts artifacts: 'docs/_build/latex/*.pdf', followSymlinks: false
            }
        }
		stage('Build Dist.') {
            steps {
				bat '.venv\\Scripts\\activate & python -m build'
				archiveArtifacts artifacts: 'dist/*.whl', followSymlinks: false
				archiveArtifacts artifacts: 'dist/*.zip', followSymlinks: false
				// Unfortunately, there's no easy way to make a .zip sdist.
            }
        }
		stage('Archive Source') {
			steps {
				fileOperations ([
					folderDeleteOperation(folderPath: '.eggs'),
					folderDeleteOperation(folderPath: '.mypy_cache'),
					folderDeleteOperation(folderPath: '.pytest_cache'),
					folderDeleteOperation(folderPath: '.tox'),
					folderDeleteOperation(folderPath: '.venv'),
					folderDeleteOperation(folderPath: 'build'),
					folderDeleteOperation(folderPath: 'dist'),
					folderDeleteOperation(folderPath: 'docs/_build'),
					folderDeleteOperation(folderPath: "${pkg_name}.egg-info"),
					fileDeleteOperation(includes: 'vers.txt'),
					fileDeleteOperation(includes: '**/__pycache__/*'),
				])
				powershell "Get-ChildItem -Filter __pycache__ -Recurse -Force | Remove-Item -Recurse -Force"
				powershell "Get-ChildItem -Path .\\* -Force | Compress-Archive -DestinationPath ${pkg_name}.v${currentBuild.displayName}.zip"
				archiveArtifacts artifacts: "${pkg_name}.*.zip", followSymlinks: false
				fileOperations([fileDeleteOperation(includes: "${pkg_name}.*.zip")])
			}
		}
    }
}
