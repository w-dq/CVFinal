import torch.nn as nn
import math
import torch.utils.model_zoo as model_zoo

model_urls = {
    'resnet18': 'https://download.pytorch.org/models/resnet18-5c106cde.pth',
    'resnet34': 'https://download.pytorch.org/models/resnet34-333f7ec4.pth',
    'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
    'resnet101': 'https://download.pytorch.org/models/resnet101-5d3b4d8f.pth',
    'resnet152': 'https://download.pytorch.org/models/resnet152-b121ed2d.pth',
}


def conv3x3(indepth, depth, stride=1):
    return nn.Conv2d(indepth, depth, kernel_size=3, stride=stride, padding=1, bias=False)

def conv1x1(indepth, depth):
    return nn.Conv2d(indepth, depth, kernel_size=1,bias=False)

class BasicBlock(nn.Module):
    expansion = 1
    #indepth: depth of input image
    #depth: depth of output image
    #size: image size = size*size
    def __init__(self, indepth, depth, stride=1, downsample=None, size=64):
        super(BasicBlock, self).__init__() # why
        self.conv1 = conv3x3(indepth, depth, stride) # stride = 1 or 2
        self.conv2 = conv3x3(depth, depth)   #default: stride = 1
        self.bn1 = nn.BatchNorm2d(depth)
        self.relu = nn.ReLU(inplace=True)
        self.bn2 = nn.BatchNorm2d(depth)

        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        input = x

        y = self.conv1(x)
        y = self.bn1(y)
        y = self.relu(y)

        y = self.conv2(y)
        y = self.bn2(y)

        if self.downsample is not None:
            input = self.downsample(input)

        return self.relu(y+input)

class BottleNeck(nn.Module):
    expansion = 4  
    #indepth: depth of input image
    #depth: depth of output image
    #size: image size = size*size
    def __init__(self, indepth, depth, stride=1, downsample=None, size=64):
        super(BottleNeck, self).__init__() # why
        self.conv1 = conv1x1(indepth, depth)
        self.conv2 = conv3x3(depth, depth, stride)
        self.conv3 = conv1x1(depth, depth*4)
        self.bn1 = nn.BatchNorm2d(depth)
        self.bn2 = nn.BatchNorm2d(depth)
        self.bn3 = nn.BatchNorm2d(depth * 4)
        self.relu = nn.ReLU(inplace=True)

        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        input = x

        y = self.conv1(x)
        y = self.bn1(y)
        y = self.relu(y)

        y = self.conv2(y)
        y = self.bn2(y)
        y = self.relu(y)
        
        y = self.conv3(y)
        y = self.bn3(y)

        if self.downsample is not None:
            input = self.downsample(input)
        
        return self.relu(y+input)

class ResNet(nn.Module):
    def __init__(self, block, layers, num_classes = 1000):
        #layers is a list: four layers, which contain how many blocks
        self.indepth = 64
        super(ResNet,self).__init__()
        #input img = 224 * 224 * 3
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        #112 * 112 * 64
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        #stride = 2
        #56 * 56 * 64
        self.layer1 = self._make_layer(block, 64, layers[0])
        #56 * 56 * 64
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        #28 * 28 * 128
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        #14 * 14 * 256
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        #7 * 7 * 512
        self.avgpool = nn.AvgPool2d(7, stride=1)
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2./n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, depth, num_blocks, stride = 1):
        downsample = None
        if stride != 1 or self.indepth != depth * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.indepth, depth * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(depth * block.expansion),
            )
        this_layer = []
        this_layer.append(block(self.indepth, depth, stride, downsample)) # only the first stride might be 2 or 1

        self.indepth = depth * block.expansion
        for _ in range(1, num_blocks):
            this_layer.append(block(self.indepth, depth))
        return nn.Sequential(*this_layer)

    def forward(self, x):
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.maxpool(out)

        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)

        out = self.avgpool(out)
        out = out.view(out.size(0), -1)

        return out

def resnet18(pretrained=False, **kwargs):
    model = ResNet(BasicBlock, [2, 2, 2, 2], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet18']))
    return model

def resnet34(pretrained=False, **kwargs):
    model = ResNet(BasicBlock, [3, 4, 6, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet34']))
    return model

def resnet50(pretrained=False, **kwargs):
    model = ResNet(BottleNeck, [3, 4, 6, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet50']))
    return model

def resnet101(pretrained=False, **kwargs):
    model = ResNet(BottleNeck, [3, 4, 23, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet101']))
    return model

def resnet152(pretrained=False, **kwargs):
    model = ResNet(BottleNeck, [3, 8, 36, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet152']))
    return model