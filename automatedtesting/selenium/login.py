name: Azure Pipeline

variables:
  - group: azsecret

stages:
  - stage: Provision
    jobs:
      - job: TerrafromTasks
        displayName: Terraform Tasks
        pool: myAgentPool
        steps:
        - task: DownloadSecureFile@1
          displayName: Download azsecret.conf file
          name: azsecret
          inputs:
            secureFile: 'azsecret.conf'
        - task: InstallSSHKey@0
          displayName: Install SSH Key
          inputs:
            knownHostsEntry: 'known_hosts'
            sshPublicKey: '$(public_key)'
            sshKeySecureFile: 'az_eqr_id_rsa'
            
        - task: TerraformInstaller@0
          displayName: Install terraform
          inputs:
            terraformVersion: 'latest'

        #- task: TerraformInstaller@0
          #displayName: Install Terraform
          #inputs:
            #terraformVersion: '1.2.9'
        - task: TerraformCLI@0
          displayName: Terraform Init
          inputs:
            command: 'init'
            workingDirectory: '$(System.DefaultWorkingDirectory)/terraform/environment/test'
            commandOptions: '-backend-config=$(azsecret.secureFilePath)'
            backendType: 'azurerm'
            backendServiceArm: 'service-connection-azurerm'
            backendAzureRmResourceGroupName: 'Azuredevops'
            backendAzureRmStorageAccountName: 'tfstate13569'
            backendAzureRmContainerName: 'tfstate'
            allowTelemetryCollection: true
          
        - task: TerraformCLI@0
          displayName: Terraform Validate
          inputs:
            command: 'validate'
            allowTelemetryCollection: true    
        
        - task: AzureCLI@1
          displayName: Set Environment Variables for Terraform
          inputs:
            azureSubscription: service-connection-azurerm
            scriptLocation: inlineScript
            workingDirectory: '$(System.DefaultWorkingDirectory)/terraform/environment/test'
            addSpnToEnvironment: true
            inlineScript: |
                export ARM_CLIENT_ID=$(client_id)
                export ARM_CLIENT_SECRET=$(client_secret)
                export ARM_SUBSCRIPTION_ID=$(subscription_id)
                export ARM_TENANT_ID=$(tenant_id)
          
        - task: TerraformCLI@0
          displayName: 'Terraform Plan'
          inputs:        
              command: 'plan'
              environmentServiceName: 'service-connection-azurerm'
              allowTelemetryCollection: true
              workingDirectory: '$(System.DefaultWorkingDirectory)/terraform/environment/test'
              
        - task: TerraformCLI@0
          displayName: Terraform Apply
          inputs:
            command: 'apply'
            environmentServiceName: 'service-connection-azurerm'
            workingDirectory: '$(System.DefaultWorkingDirectory)/terraform/environment/test'
            allowTelemetryCollection: true

  - stage: Build
    jobs:
      - job: Build_Artifacts
        displayName: Build Artifacts
        pool: myAgentPool
        steps:
          - task: ArchiveFiles@2
            displayName: Archive Fakerestapi
            inputs:
              rootFolderOrFile: '$(System.DefaultWorkingDirectory)/automatedtesting/jmeter/fakerestapi'
              includeRootFolder: false
              archiveType: 'zip'
              archiveFile: '$(Build.ArtifactStagingDirectory)/fakerestapi-$(Build.BuildId).zip'
          
          - task: PublishPipelineArtifact@1
            displayName: Publish Fakerestapi as Artifact
            inputs:
              targetPath: '$(Build.ArtifactStagingDirectory)/fakerestapi-$(Build.BuildId).zip'
              artifactName: 'drop-fakerestapi'
              
          - task: ArchiveFiles@2
            displayName: Archive Selenium
            inputs:
              rootFolderOrFile: '$(System.DefaultWorkingDirectory)/automatedtesting/selenium'
              includeRootFolder: false
              archiveType: 'zip'
              archiveFile: '$(Build.ArtifactStagingDirectory)/selenium-$(Build.BuildId).zip'
          - task: PublishPipelineArtifact@1
            displayName: Publish Selenium Artifact
            inputs:
              targetPath: '$(Build.ArtifactStagingDirectory)/selenium-$(Build.BuildId).zip'
              artifactName: 'drop-selenium'

          - task: ArchiveFiles@2
            displayName: 'Archive PerformanceTestSuite'
            inputs:
              rootFolderOrFile: '$(System.DefaultWorkingDirectory)/automatedtesting/jmeter'
              includeRootFolder: false
              archiveType: 'zip'
              archiveFile: '$(Build.ArtifactStagingDirectory)/jtest-$(Build.BuildId).zip'
          - task: PublishBuildArtifacts@1
            displayName: Publish Jmeter test
            inputs:
              targetPath: '$(Build.ArtifactStagingDirectory)/jtest-$(Build.BuildId).zip'
              ArtifactName: 'drop-jtest'


  - stage: Deploy 
    jobs:
      - deployment: deploy_fakerestapi
        displayName: Deploy FakeRestAPI
        pool: myAgentPool
        environment: 'TEST'
        strategy:
          runOnce:
            deploy:
              steps:
              - task: AzureRmWebAppDeployment@4
                inputs:
                  ConnectionType: 'AzureRM'
                  azureSubscription: 'service-connection-azurerm'
                  appType: 'webApp'
                  WebAppName: 'p3demo-AppService'
                  packageForLinux: '$(Pipeline.Workspace)/drop-fakerestapi/fakerestapi-$(Build.BuildId).zip'
                  DeploymentType: zipDeploy 

      - deployment: VMDeploy
        displayName: Deploy Virtual Machine
        environment:
          name: 'TEST'
          resourceType: VirtualMachine
        strategy:
          runOnce:
            deploy:
              steps:
                - bash: |
                    sudo apt-get update -y
                    sudo apt-get install python3-pip -y
                    sudo apt-get install unzip -y
                    sudo apt-get install -y chromium-browser
                    sudo apt-get install -y chromium-chromedriver
                    python3 -m pip install --upgrade pip
                    pip3 install selenium
                    # Install Log Analytics agent on Linux computers (only need to run once, comment when installed)
                    # wget https://raw.githubusercontent.com/Microsoft/OMS-Agent-for-Linux/master/installer/scripts/onboard_agent.sh && sh onboard_agent.sh -w ${AZURE_LOG_ANALYTICS_ID} -s ${AZURE_LOG_ANALYTICS_PRIMARY_KEY} -d opinsights.azure.com
                  env: 
                    AZURE_LOG_ANALYTICS_ID: $(la_workspace_id)
                    AZURE_LOG_ANALYTICS_PRIMARY_KEY: $(la_primary_key)
                  displayName: Configure VM 

  - stage: Test
    jobs:
    - job: IntegrationTests
      displayName: Integration Tests For UI and Selenium
      pool: myAgentPool
      steps:
      - task: CmdLine@2
        displayName: Install Newman
        inputs:
          script: 'sudo npm install -g newman'
          workingDirectory: $(System.DefaultWorkingDirectory)
      - task: CmdLine@2
        displayName: Apply Regression Tests
        continueOnError: true
        inputs:
          script: 'newman run ./automatedtesting/postman/regression.json --reporters cli,junit --reporter-junit-export ./automatedtesting/postman/TEST-regression.xml'
          workingDirectory:  $(System.DefaultWorkingdirectory)
      - task: CmdLine@2
        displayName: Apply Validation Tests
        continueOnError: true
        inputs:
          script: 'newman run ./automatedtesting/postman/validation.json --reporters cli,junit --reporter-junit-export ./automatedtesting/postman/TEST-validation.xml'
          workingDirectory: $(System.DefaultWorkingdirectory)
      - task: PublishTestResults@2
        displayName: Publish Test Results
        inputs:
          testResultsFiles: '**/TEST-*.xml' 
          searchFolder: '$(System.DefaultWorkingDirectory)/automatedtesting/postman/' 
          publishRunAttachments: true

    - job: UITests
      displayName: Selenuim UI Tests
      pool: myAgentPool
      steps:
      - task: Bash@3
        displayName: 'Setup VM environment'
        inputs:
          targetType: 'inline'
          script: |
            #! /bin/bash
            sudo apt-get upgrade -y
            sudo apt-get install python3-pip -y
            sudo apt-get install unzip -y
      - task: Bash@3
        displayName: 'Configure Selenium, Chromium & chromedriver'
        inputs:
          targetType: 'inline'
          script: |
            #install chromium & selenium
            sudo apt-get install -y chromium-browser
            pip3 install selenium
            
            #install chromedriver & export path
            if [ ! -f $(Pipeline.Workspace)/chromedriver ]; then
              wget https://chromedriver.storage.googleapis.com/100.0.4896.20/chromedriver_linux64.zip
              unzip chromedriver_linux64.zip
            fi
            export PATH=$PATH:$(Pipeline.Workspace)/chromedriver
      - task: Bash@3
        displayName: 'Run UI test'
        inputs:
          targetType: 'inline'
          script: |
            if [ ! -d /var/log/selenium ]; then
                  sudo mkdir /var/log/selenium
                  sudo chmod 777 /var/log/selenium
            fi            
            python3 ./automatedtesting/selenium/login.py 2>&1 | sudo tee -a /var/log/selenium/selenium-test.log
            cd $(System.DefaultWorkingDirectory)
            mkdir -p log/selenium              
            sudo cp /var/log/selenium/selenium-test.log log/selenium/selenium-test.log
            ls -al
      - task: PublishPipelineArtifact@1
        displayName: Publish selenium logs
        inputs:
          targetPath: '$(System.DefaultWorkingDirectory)/log/selenium/selenium-test.log'
          artifact: 'drop-selenium-logs'
          publishLocation: 'pipeline'

    - job: PerformanceTest
      displayName: Test JMeter
      pool: myAgentPool
      steps:
          - bash: |
              echo  '$(System.DefaultWorkingDirectory)'
              ls -al
              pwd
              unzip -o $(Pipeline.Workspace)/drop-jtest/jtest-$(Build.BuildId).zip -d .
              sudo apt-get install openjdk-11-jre-headless -y
              java -version
              wget https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.5.tgz -O jmeter.tgz
              tar xzvf jmeter.tgz
              mkdir -p log/jmeter
              # if [ ! -d /var/log/jmeter ]; then
              #         sudo mkdir /var/log/jmeter
              #         sudo chmod 777 /var/log/jmeter
              # fi
              # if [ ! -d /var/log/jmeter/endurance_test_report ]; then
              #         sudo mkdir /var/log/jmeter/stress_test_report
              #         sudo chmod 777 /var/log/jmeter/stress_test_report
              # fi  
              # if [ ! -d /var/log/jmeter/endurance_test_report ]; then
              #         sudo mkdir /var/log/jmeter/endurance_test_report
              #         sudo chmod 777 /var/log/jmeter/endurance_test_report
              # fi  
              ls -la
              pwd  
            displayName: Install JMeter
          - bash: |
              apache-jmeter-5.5/bin/jmeter -n -t demo_stress.jmx \
                                          -l log/jmeter/stress-test-result.csv \
                                          -e -f -o log/jmeter \
                                          -j log/jmeter/jmeter-stress-test.log
            displayName: JMeter Stress Test
          - bash: |
              apache-jmeter-5.5/bin/jmeter -n -t demo_endurance.jmx \
                                          -l log/jmeter/endurance-test-result.csv \
                                          -e -f -o log/jmeter \
                                          -j log/jmeter/jmeter-endurance-test.log
            displayName: JMeter Endurance Test
          - task: ArchiveFiles@2
            displayName: Saving JMeter stress test report to artifact
            inputs:
              rootFolderOrFile: '$(System.DefaultWorkingDirectory)/log/jmeter'
              includeRootFolder: false
              archiveType: 'zip'
              archiveFile: '$(System.DefaultWorkingDirectory)/log/jmeter-$(Build.BuildId).zip'
              verbose: true
          - task: ArchiveFiles@2
            displayName: Saving JMeter endurance test report to artifact
            inputs:
              rootFolderOrFile: '$(System.DefaultWorkingDirectory)/log/jmeter'
              includeRootFolder: false
              archiveType: 'zip'
              archiveFile: '$(System.DefaultWorkingDirectory)/log/jmeter-$(Build.BuildId).zip'
              verbose: true
          - task: PublishPipelineArtifact@1
            displayName: Publish JMeter logs
            inputs:
              targetPath: '$(System.DefaultWorkingDirectory)/log/jmeter'
              artifactName: 'drop-jmeter-logs'
